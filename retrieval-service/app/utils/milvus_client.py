"""Milvus client wrapper."""
from typing import List, Dict, Any, Optional
from pymilvus import Collection, connections, utility
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MilvusClient:
    """Milvus client for vector search."""
    
    def __init__(self):
        """Initialize Milvus client."""
        self.host = settings.milvus_host
        self.port = settings.milvus_port
        self.user = settings.milvus_user
        self.password = settings.milvus_password
        self.collection_name = settings.milvus_collection_name
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Milvus."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                user=self.user if self.user else None,
                password=self.password if self.password else None,
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}", exc_info=True)
            self._connected = False
            return False
    
    def search(
        self,
        query_vectors: List[List[float]],
        anns_field: str = "embedding",
        limit: int = 10,
        output_fields: Optional[List[str]] = None,
    ) -> Optional[List[Any]]:
        """
        Search for similar vectors.
        
        Returns:
            List of search results, each containing entities with chunk_id, text, and distance
        """
        try:
            if not self._connected:
                if not self.connect():
                    return None
            
            collection = Collection(self.collection_name)
            collection.load()
            
            if output_fields is None:
                output_fields = ["chunk_id", "text"]
            
            # Search parameters
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            
            results = collection.search(
                data=query_vectors,
                anns_field=anns_field,
                param=search_params,
                limit=limit,
                output_fields=output_fields,
            )
            
            logger.info(f"Searched with {len(query_vectors)} queries, limit={limit}")
            return results
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return None

