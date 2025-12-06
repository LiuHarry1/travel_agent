"""Retrieval service implementation."""
from typing import List, Dict, Any, Optional
from app.utils.milvus_client import MilvusClient
from app.utils.embedders import create_embedder, BaseEmbedder
from app.utils.rerank import rerank_chunks
from app.utils.llm_filter import QwenLLMFilter
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalService:
    """Main retrieval service."""
    
    def __init__(self):
        """Initialize retrieval service."""
        self.milvus_client = MilvusClient()
        self.embedders: Dict[str, BaseEmbedder] = {}
        self.llm_filter = QwenLLMFilter(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=settings.qwen_model
        )
        self._initialize_embedders()
    
    def _initialize_embedders(self):
        """Initialize embedding models."""
        for model_config in settings.embedding_models:
            parts = model_config.split(":", 1)
            if len(parts) == 2:
                provider, model = parts
            else:
                provider = parts[0]
                model = None
            
            try:
                embedder = create_embedder(provider, model)
                key = f"{provider}:{model}" if model else provider
                self.embedders[key] = embedder
                logger.info(f"Initialized embedder: {key}")
            except Exception as e:
                logger.error(f"Failed to initialize embedder {model_config}: {e}", exc_info=True)
    
    def _search_with_embedder(
        self,
        query: str,
        embedder: BaseEmbedder,
        embedder_name: str
    ) -> List[Dict[str, Any]]:
        """Search using a single embedder."""
        try:
            # Generate embedding
            embeddings = embedder.embed([query])
            if not embeddings:
                logger.warning(f"No embedding generated for {embedder_name}")
                return []
            
            # Search in Milvus
            results = self.milvus_client.search(
                query_vectors=embeddings,
                limit=settings.top_k_per_model,
                output_fields=["chunk_id", "text"]
            )
            
            if not results:
                return []
            
            # Format results
            # Milvus search returns a list of lists (one per query vector)
            # Each element is a list of Hit objects
            formatted_results = []
            for hit_list in results:
                for hit in hit_list:
                    # Hit object has: id, distance, entity (dict with output_fields)
                    entity = hit.entity if hasattr(hit, 'entity') else {}
                    chunk_id = entity.get("chunk_id") if isinstance(entity, dict) else None
                    text = entity.get("text", "") if isinstance(entity, dict) else ""
                    distance = hit.distance if hasattr(hit, 'distance') else 0.0
                    
                    if chunk_id is not None:
                        formatted_results.append({
                            "chunk_id": chunk_id,
                            "text": text,
                            "score": distance,
                            "embedder": embedder_name
                        })
            
            logger.info(f"Found {len(formatted_results)} results with {embedder_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error with {embedder_name}: {e}", exc_info=True)
            return []
    
    def _deduplicate_by_chunk_id(
        self,
        all_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Deduplicate results by chunk_id, keeping the best score."""
        seen = {}
        for result in all_results:
            chunk_id = result["chunk_id"]
            if chunk_id not in seen:
                seen[chunk_id] = result
            else:
                # Keep the one with better (lower) distance score
                if result["score"] < seen[chunk_id]["score"]:
                    seen[chunk_id] = result
        
        deduplicated = list(seen.values())
        logger.info(f"Deduplicated from {len(all_results)} to {len(deduplicated)} chunks")
        return deduplicated
    
    def retrieve(
        self,
        query: str,
        return_debug: bool = False
    ) -> Dict[str, Any]:
        """
        Main retrieval method.
        
        Args:
            query: User query
            return_debug: If True, return all intermediate results
        
        Returns:
            Dictionary with final results and optionally debug information
        """
        logger.info(f"Starting retrieval for query: {query}")
        
        # Step 1: Search with all embedding models
        all_model_results = {}
        all_results = []
        
        for embedder_name, embedder in self.embedders.items():
            results = self._search_with_embedder(query, embedder, embedder_name)
            all_model_results[embedder_name] = results
            all_results.extend(results)
        
        # Step 2: Deduplicate by chunk_id
        deduplicated = self._deduplicate_by_chunk_id(all_results)
        
        # Step 3: Re-rank
        reranked = rerank_chunks(query, deduplicated, top_k=settings.rerank_top_k)
        
        # Step 4: LLM filtering
        final_chunks = self.llm_filter.filter_chunks(
            query,
            reranked,
            top_k=settings.final_top_k
        )
        
        # Format final results
        final_results = [
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"]
            }
            for chunk in final_chunks
        ]
        
        result = {
            "query": query,
            "results": final_results
        }
        
        if return_debug:
            result["debug"] = {
                "model_results": all_model_results,
                "deduplicated": deduplicated,
                "reranked": reranked,
                "final": final_chunks
            }
        
        logger.info(f"Retrieval completed: {len(final_results)} final chunks")
        return result

