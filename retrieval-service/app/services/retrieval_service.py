"""Retrieval service implementation."""
from typing import List, Dict, Any, Optional, Tuple
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.infrastructure.config.pipeline_config import PipelineConfig
from app.infrastructure.vector_store.milvus_client import MilvusClient
from app.infrastructure.embedders import create_embedder
from app.core.services.embedder import Embedder
from app.core.services.reranker import Reranker
from app.core.services.llm_filter import LLMFilter
from app.infrastructure.rerankers import create_reranker
from app.infrastructure.llm import create_llm_filter
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Type aliases for better readability
ChunkResult = Dict[str, Any]
ChunkResults = List[ChunkResult]
ModelResults = Dict[str, ChunkResults]


class RetrievalService:
    """Main retrieval service."""
    
    # Constants
    MS_TO_SECONDS = 1000
    OUTPUT_FIELDS = ["id", "text"]
    DEFAULT_DISTANCE = 0.0
    
    def __init__(self, pipeline_config: PipelineConfig):
        """Initialize retrieval service with pipeline configuration."""
        self.config = pipeline_config
        self.milvus_client = MilvusClient(pipeline_config.milvus)
        self.embedders: Dict[str, Embedder] = {}
        self.reranker: Reranker = create_reranker(pipeline_config.rerank)
        self.llm_filter: LLMFilter = create_llm_filter(pipeline_config.llm_filter)
        self._embedder_collections: Dict[str, str] = {}
        self._initialize_embedders()
    
    def _initialize_embedders(self) -> None:
        """Initialize embedding models from pipeline configuration."""
        from app.infrastructure.config.pipeline_config import EmbeddingModelConfig
        
        model_configs = self.config.get_embedding_model_configs()
        if not model_configs:
            raise ValueError("No embedding models configured in pipeline")
        
        successful_count = 0
        for model_config in model_configs:
            if isinstance(model_config, EmbeddingModelConfig):
                model_str = model_config.model
                collection = model_config.collection or self.config.milvus.collection
            else:
                # Fallback for old format
                model_str = str(model_config)
                collection = self.config.milvus.collection
            
            # Parse model string: "provider:model" or "provider"
            parts = model_str.split(":", 1)
            provider = parts[0]
            model = parts[1] if len(parts) == 2 else None
            
            try:
                embedder = create_embedder(provider, model)
                embedder_key = f"{provider}:{model}" if model else provider
                self.embedders[embedder_key] = embedder
                self._embedder_collections[embedder_key] = collection
                successful_count += 1
                logger.info(f"Initialized embedder: {embedder_key} -> collection: {collection}")
            except Exception as e:
                logger.error(f"Failed to initialize embedder {model_str}: {e}", exc_info=True)
        
        if successful_count == 0:
            raise ValueError("Failed to initialize any embedder. Please check your configuration.")
    
    def _get_collection_name(self, embedder_name: str) -> str:
        """Get collection name for embedder, fallback to default."""
        return self._embedder_collections.get(
            embedder_name,
            self.config.milvus.collection
        )
    
    def _format_hit_result(self, hit: Any, embedder_name: str) -> Optional[ChunkResult]:
        """Extract chunk data from Milvus hit object."""
        chunk_id = getattr(hit, 'id', None)
        if chunk_id is None:
            logger.warning(f"Hit object missing id: {hit}")
            return None
        
        distance = getattr(hit, 'distance', self.DEFAULT_DISTANCE)
        entity = getattr(hit, 'entity', {})
        
        # Extract text from entity (dict or object)
        if isinstance(entity, dict):
            text = entity.get("text", "")
        else:
            text = getattr(entity, "text", "")
        
        if not text:
            logger.warning(f"Chunk {chunk_id} has no text content in search results")
        
        return {
            "chunk_id": chunk_id,
            "text": text or "",
            "score": distance,
            "embedder": embedder_name
        }
    
    def _search_with_embedder(
        self,
        query: str,
        embedder: Embedder,
        embedder_name: str
    ) -> ChunkResults:
        """Search using a single embedder with its corresponding collection."""
        try:
            # Generate embedding
            embeddings = embedder.embed([query])
            if not embeddings:
                logger.warning(f"No embedding generated for {embedder_name}")
                return []
            
            # Get collection and search limit
            collection_name = self._get_collection_name(embedder_name)
            search_limit = min(
                self.config.chunk_sizes.initial_search,
                self.config.retrieval.top_k_per_model
            )
            
            # Search in Milvus
            results = self.milvus_client.search(
                query_vectors=embeddings,
                limit=search_limit,
                output_fields=self.OUTPUT_FIELDS,
                collection_name=collection_name
            )
            
            if results is None:
                logger.warning(f"Milvus search returned None for {embedder_name}")
                return []
            
            if not results:
                return []
            
            # Format results: Milvus returns list of lists (one per query vector)
            formatted_results = []
            for hit_list in results:
                for hit in hit_list:
                    chunk_result = self._format_hit_result(hit, embedder_name)
                    if chunk_result:
                        formatted_results.append(chunk_result)
            
            logger.info(f"Found {len(formatted_results)} results with {embedder_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error with {embedder_name}: {e}", exc_info=True)
            return []
    
    def _deduplicate_by_chunk_id(self, all_results: ChunkResults) -> ChunkResults:
        """Deduplicate results by chunk_id, keeping the best score."""
        seen = {}
        for result in all_results:
            chunk_id = result.get("chunk_id")
            if chunk_id is None:
                logger.warning(f"Result missing chunk_id, skipping: {result}")
                continue
            
            if chunk_id not in seen:
                seen[chunk_id] = result
            else:
                # Keep the one with better (lower) distance score
                current_score = result.get("score", float('inf'))
                existing_score = seen[chunk_id].get("score", float('inf'))
                if current_score < existing_score:
                    seen[chunk_id] = result
        
        deduplicated = list(seen.values())
        logger.info(f"Deduplicated from {len(all_results)} to {len(deduplicated)} chunks")
        return deduplicated
    
    def _search_with_all_embedders(self, query: str) -> Tuple[ModelResults, ChunkResults]:
        """Search with all embedders in parallel."""
        start_time = time.perf_counter()
        model_results: ModelResults = {}
        combined_results: ChunkResults = []
        
        def search_with_timing(embedder_name: str, embedder: Embedder) -> Tuple[str, ChunkResults, float]:
            """Wrapper to measure search time."""
            step_start = time.perf_counter()
            try:
                results = self._search_with_embedder(query, embedder, embedder_name)
                elapsed_ms = (time.perf_counter() - step_start) * self.MS_TO_SECONDS
                return embedder_name, results, elapsed_ms
            except Exception as e:
                logger.error(f"Error in parallel search for {embedder_name}: {e}", exc_info=True)
                elapsed_ms = (time.perf_counter() - step_start) * self.MS_TO_SECONDS
                return embedder_name, [], elapsed_ms
        
        # Execute all embedders in parallel
        with ThreadPoolExecutor(max_workers=len(self.embedders)) as executor:
            future_to_name = {
                executor.submit(search_with_timing, name, embedder): name
                for name, embedder in self.embedders.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_name):
                embedder_name, results, elapsed_ms = future.result()
                model_results[embedder_name] = results
                combined_results.extend(results)
                self._debug_timing[f"embed_{embedder_name}"] = elapsed_ms
        
        self._debug_timing["embedding_total"] = (time.perf_counter() - start_time) * self.MS_TO_SECONDS
        return model_results, combined_results
    
    def _rerank_chunks(self, query: str, chunks: ChunkResults) -> ChunkResults:
        """Re-rank chunks based on relevance."""
        start_time = time.perf_counter()
        
        rerank_limit = min(
            self.config.chunk_sizes.rerank_input,
            self.config.retrieval.rerank_top_k,
            len(chunks)
        )
        
        reranked = self.reranker.rerank(
            query,
            chunks[:rerank_limit],
            top_k=self.config.retrieval.rerank_top_k
        )
        
        self._debug_timing["reranking"] = (time.perf_counter() - start_time) * self.MS_TO_SECONDS
        return reranked
    
    def _filter_with_llm(self, query: str, chunks: ChunkResults) -> ChunkResults:
        """Filter chunks using LLM."""
        start_time = time.perf_counter()
        
        llm_limit = min(
            self.config.chunk_sizes.llm_filter_input,
            len(chunks)
        )
        
        final_chunks = self.llm_filter.filter_chunks(
            query,
            chunks[:llm_limit],
            top_k=self.config.retrieval.final_top_k
        )
        
        self._debug_timing["llm_filtering"] = (time.perf_counter() - start_time) * self.MS_TO_SECONDS
        return final_chunks
    
    def _format_final_results(self, chunks: ChunkResults) -> List[Dict[str, Any]]:
        """Format chunks for final output."""
        final_results = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            if chunk_id is None:
                logger.warning(f"Skipping chunk without chunk_id: {chunk}")
                continue
            
            text = chunk.get("text", "")
            if not text:
                logger.warning(f"Chunk {chunk_id} has no text content")
            
            final_results.append({
                "chunk_id": chunk_id,
                "text": text
            })
        
        return final_results
    
    def _build_response(
        self,
        query: str,
        final_results: List[Dict[str, Any]],
        return_debug: bool,
        debug_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the final response dictionary."""
        result = {
            "query": query,
            "results": final_results
        }
        
        if return_debug:
            result["debug"] = {
                **debug_data,
                "timing": self._debug_timing
            }
        
        return result
    
    def _is_rerank_enabled(self) -> bool:
        """Check if rerank is enabled (has valid api_url)."""
        return (
            self.config.rerank is not None and
            self.config.rerank.api_url and
            self.config.rerank.api_url.strip() != ""
        )
    
    def _is_llm_filter_enabled(self) -> bool:
        """Check if LLM filter is enabled (has valid base_url or model)."""
        return (
            self.config.llm_filter is not None and
            (
                (self.config.llm_filter.base_url and self.config.llm_filter.base_url.strip() != "") or
                (self.config.llm_filter.model and self.config.llm_filter.model.strip() != "")
            )
        )
    
    def retrieve(
        self,
        query: str,
        return_debug: bool = False
    ) -> Dict[str, Any]:
        """
        Main retrieval method - orchestrates the retrieval pipeline.
        
        Args:
            query: User query
            return_debug: If True, return all intermediate results
        
        Returns:
            Dictionary with final results and optionally debug information
        """
        logger.info(f"Starting retrieval for query: {query}")
        self._debug_timing = {}
        start_total = time.perf_counter()
        
        # Execute retrieval pipeline steps
        model_results, combined_results = self._search_with_all_embedders(query)
        
        start_dedup = time.perf_counter()
        deduplicated = self._deduplicate_by_chunk_id(combined_results)
        self._debug_timing["deduplication"] = (time.perf_counter() - start_dedup) * self.MS_TO_SECONDS
        
        # Conditionally execute rerank
        reranked = deduplicated
        if self._is_rerank_enabled():
            reranked = self._rerank_chunks(query, deduplicated)
        else:
            logger.info("Rerank is disabled, skipping rerank step")
        
        # Conditionally execute LLM filter
        if self._is_llm_filter_enabled():
            final_chunks = self._filter_with_llm(query, reranked)
        else:
            logger.info("LLM filter is disabled, using reranked results as final")
            final_chunks = reranked
        
        final_results = self._format_final_results(final_chunks)
        
        # Record total time
        self._debug_timing["total"] = (time.perf_counter() - start_total) * self.MS_TO_SECONDS
        
        logger.info(
            f"Retrieval completed: {len(final_results)} final chunks "
            f"(Total time: {self._debug_timing['total']:.2f} ms)"
        )
        
        # Build debug data conditionally
        debug_data: Dict[str, Any] = {
            "model_results": model_results,
            "deduplicated": deduplicated,
        }
        
        if self._is_rerank_enabled():
            debug_data["reranked"] = reranked
        
        # Always include final results, but only mark as llm_filtered if enabled
        debug_data["final"] = final_chunks
        # Add a flag to indicate if LLM filter was used
        if not self._is_llm_filter_enabled():
            # Remove llm_filtering timing if not enabled
            if "llm_filtering" in self._debug_timing:
                del self._debug_timing["llm_filtering"]
            if "llm_filter" in self._debug_timing:
                del self._debug_timing["llm_filter"]
        
        return self._build_response(query, final_results, return_debug, debug_data)
