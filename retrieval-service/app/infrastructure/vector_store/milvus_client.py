"""Milvus client wrapper."""
from typing import List, Dict, Any, Optional
from pymilvus import Collection
from app.infrastructure.config.pipeline_config import MilvusConfig
from app.infrastructure.vector_store.connection_pool import milvus_connection_pool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MilvusClient:
    """Milvus client for vector search."""
    
    def __init__(self, config: MilvusConfig):
        """Initialize Milvus client with project configuration."""
        self.config = config
        self.host = config.host
        self.port = config.port
        self.user = config.user
        self.password = config.password
        self.database = config.database
        self.collection_name = config.collection
    
    def _get_connection_alias(self) -> Optional[str]:
        """Get connection alias from pool."""
        return milvus_connection_pool.get_alias(self.config)
    
    def search(
        self,
        query_vectors: List[List[float]],
        anns_field: str = "embedding",
        limit: int = 10,
        output_fields: Optional[List[str]] = None,
        collection_name: Optional[str] = None,
    ) -> Optional[List[Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vectors: Query vectors to search
            anns_field: Field name for vector search
            limit: Number of results to return
            output_fields: Fields to return in results
            collection_name: Override collection name (if None, uses self.collection_name)
        
        Returns:
            List of search results, each containing entities with chunk_id, text, and distance
        """
        try:
            alias = self._get_connection_alias()
            if not alias:
                logger.error("Failed to get Milvus connection")
                return None
            
            # Use specified collection or default
            collection_to_use = collection_name or self.collection_name
            
            # Use collection with database and alias
            collection = Collection(collection_to_use, using=alias)
            collection.load()
            
            if output_fields is None:
                output_fields = ["id", "text"]
            
            # Search parameters
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            
            results = collection.search(
                data=query_vectors,
                anns_field=anns_field,
                param=search_params,
                limit=limit,
                output_fields=output_fields,
            )
            
            logger.info(f"Searched with {len(query_vectors)} queries, limit={limit}, collection={collection_to_use}, output_fields={output_fields}")
            # Debug: log first result structure
            if results and len(results) > 0 and len(results[0]) > 0:
                first_hit = results[0][0]
                logger.info(f"First hit type: {type(first_hit)}")
                logger.info(f"First hit attributes: {[attr for attr in dir(first_hit) if not attr.startswith('_')]}")
                if hasattr(first_hit, 'entity'):
                    logger.info(f"First hit.entity: {first_hit.entity}")
            
            return results
        except Exception as e:
            logger.error(f"Search error in collection {collection_name or self.collection_name}: {e}", exc_info=True)
            return None

