"""Milvus vector database client with common operations."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
        MilvusException,
    )
except ImportError:
    raise ImportError(
        "pymilvus is not installed. Install it with: pip install pymilvus"
    )

from app.logger import get_logger

logger = get_logger(__name__)


class MilvusClient:
    """Milvus vector database client with common operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        user: str = "",
        password: str = "",
        alias: str = "default",
    ):
        """
        Initialize Milvus client.

        Args:
            host: Milvus server host (default: "localhost")
            port: Milvus server port (default: 19530)
            user: Username for authentication (default: "")
            password: Password for authentication (default: "")
            alias: Connection alias (default: "default")
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.alias = alias
        self._connected = False

    def connect(self) -> bool:
        """
        Connect to Milvus server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            connections.connect(
                alias=self.alias,
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

    def disconnect(self) -> None:
        """Disconnect from Milvus server."""
        try:
            if self._connected:
                connections.disconnect(alias=self.alias)
                self._connected = False
                logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {e}", exc_info=True)

    def is_connected(self) -> bool:
        """
        Check if connected to Milvus.

        Returns:
            True if connected, False otherwise
        """
        try:
            if not self._connected:
                return False
            # Try to list collections to verify connection
            utility.list_collections()
            return True
        except Exception:
            self._connected = False
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        try:
            return utility.has_collection(collection_name)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}", exc_info=True)
            return False

    def create_collection(
        self,
        collection_name: str,
        fields: List[FieldSchema],
        description: str = "",
        auto_id: bool = True,
    ) -> bool:
        """
        Create a new collection.

        Args:
            collection_name: Name of the collection
            fields: List of FieldSchema objects defining the collection schema
            description: Description of the collection
            auto_id: Whether to auto-generate IDs (default: True)

        Returns:
            True if collection created successfully, False otherwise
        """
        try:
            if self.collection_exists(collection_name):
                logger.warning(f"Collection '{collection_name}' already exists")
                return False

            schema = CollectionSchema(
                fields=fields, description=description, auto_id=auto_id
            )
            collection = Collection(
                name=collection_name, schema=schema, using=self.alias
            )
            logger.info(f"Created collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(
                f"Error creating collection '{collection_name}': {e}", exc_info=True
            )
            return False

    def create_collection_with_embedding(
        self,
        collection_name: str,
        embedding_dim: int,
        id_field_name: str = "id",
        embedding_field_name: str = "embedding",
        text_field_name: str = "text",
        metadata_fields: Optional[List[FieldSchema]] = None,
        description: str = "",
        auto_id: bool = True,
    ) -> bool:
        """
        Create a collection with embedding field (common use case).

        Args:
            collection_name: Name of the collection
            embedding_dim: Dimension of the embedding vector
            id_field_name: Name of the ID field (default: "id")
            embedding_field_name: Name of the embedding field (default: "embedding")
            text_field_name: Name of the text field (default: "text")
            metadata_fields: Optional additional metadata fields
            description: Description of the collection
            auto_id: Whether to auto-generate IDs (default: True)

        Returns:
            True if collection created successfully, False otherwise
        """
        try:
            # Define fields
            fields = []

            # ID field
            if not auto_id:
                fields.append(
                    FieldSchema(
                        name=id_field_name,
                        dtype=DataType.INT64,
                        is_primary=True,
                        auto_id=False,
                    )
                )

            # Text field
            fields.append(
                FieldSchema(name=text_field_name, dtype=DataType.VARCHAR, max_length=65535)
            )

            # Embedding field
            fields.append(
                FieldSchema(
                    name=embedding_field_name,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=embedding_dim,
                )
            )

            # Additional metadata fields
            if metadata_fields:
                fields.extend(metadata_fields)

            return self.create_collection(
                collection_name=collection_name,
                fields=fields,
                description=description,
                auto_id=auto_id,
            )
        except Exception as e:
            logger.error(
                f"Error creating collection with embedding '{collection_name}': {e}",
                exc_info=True,
            )
            return False

    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        Get a collection object.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection object if exists, None otherwise
        """
        try:
            if not self.collection_exists(collection_name):
                logger.warning(f"Collection '{collection_name}' does not exist")
                return None
            return Collection(name=collection_name, using=self.alias)
        except Exception as e:
            logger.error(
                f"Error getting collection '{collection_name}': {e}", exc_info=True
            )
            return None

    def drop_collection(self, collection_name: str) -> bool:
        """
        Drop a collection.

        Args:
            collection_name: Name of the collection to drop

        Returns:
            True if collection dropped successfully, False otherwise
        """
        try:
            if not self.collection_exists(collection_name):
                logger.warning(f"Collection '{collection_name}' does not exist")
                return False
            utility.drop_collection(collection_name)
            logger.info(f"Dropped collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(
                f"Error dropping collection '{collection_name}': {e}", exc_info=True
            )
            return False

    def insert(
        self,
        collection_name: str,
        data: List[List[Any]],
        field_names: Optional[List[str]] = None,
    ) -> Optional[List[int]]:
        """
        Insert data into a collection.

        Args:
            collection_name: Name of the collection
            data: List of lists, where each inner list represents a row of data
            field_names: Optional list of field names in order (if None, uses schema order)

        Returns:
            List of inserted IDs if successful, None otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None

            # Insert data
            result = collection.insert(data, field_names=field_names)
            collection.flush()  # Ensure data is written
            logger.info(f"Inserted {len(data)} entities into '{collection_name}'")
            return result.primary_keys
        except Exception as e:
            logger.error(
                f"Error inserting data into '{collection_name}': {e}", exc_info=True
            )
            return None

    def search(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        anns_field: str = "embedding",
        param: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        expr: Optional[str] = None,
        output_fields: Optional[List[str]] = None,
    ) -> Optional[List[Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection
            query_vectors: List of query vectors to search
            anns_field: Name of the vector field to search (default: "embedding")
            param: Search parameters (e.g., {"metric_type": "L2", "params": {"nprobe": 10}})
            limit: Number of results to return (default: 10)
            expr: Optional filter expression (e.g., "id > 100")
            output_fields: Optional list of fields to return

        Returns:
            Search results if successful, None otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None

            # Load collection if not loaded
            if not collection.has_index():
                logger.warning(
                    f"Collection '{collection_name}' has no index. Creating default index."
                )
                self.create_index(
                    collection_name=collection_name,
                    field_name=anns_field,
                    index_type="FLAT",
                    metric_type="L2",
                )

            collection.load()

            # Default search parameters
            if param is None:
                param = {"metric_type": "L2", "params": {"nprobe": 10}}

            # Perform search
            results = collection.search(
                data=query_vectors,
                anns_field=anns_field,
                param=param,
                limit=limit,
                expr=expr,
                output_fields=output_fields,
            )

            logger.info(
                f"Searched '{collection_name}' with {len(query_vectors)} query vectors, limit={limit}"
            )
            return results
        except Exception as e:
            logger.error(
                f"Error searching in '{collection_name}': {e}", exc_info=True
            )
            return None

    def query(
        self,
        collection_name: str,
        expr: str,
        output_fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Query collection with expression.

        Args:
            collection_name: Name of the collection
            expr: Query expression (e.g., "id in [1, 2, 3]")
            output_fields: Optional list of fields to return
            limit: Optional limit on number of results

        Returns:
            List of query results if successful, None otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None

            collection.load()

            results = collection.query(
                expr=expr, output_fields=output_fields, limit=limit
            )

            logger.info(f"Queried '{collection_name}' with expression: {expr}")
            return results
        except Exception as e:
            logger.error(
                f"Error querying '{collection_name}': {e}", exc_info=True
            )
            return None

    def delete(
        self,
        collection_name: str,
        expr: str,
    ) -> bool:
        """
        Delete entities from collection.

        Args:
            collection_name: Name of the collection
            expr: Delete expression (e.g., "id in [1, 2, 3]")

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return False

            collection.delete(expr)
            collection.flush()
            logger.info(f"Deleted entities from '{collection_name}' with expression: {expr}")
            return True
        except Exception as e:
            logger.error(
                f"Error deleting from '{collection_name}': {e}", exc_info=True
            )
            return False

    def create_index(
        self,
        collection_name: str,
        field_name: str,
        index_type: str = "IVF_FLAT",
        metric_type: str = "L2",
        params: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
    ) -> bool:
        """
        Create an index on a field.

        Args:
            collection_name: Name of the collection
            field_name: Name of the field to index
            index_type: Type of index (default: "IVF_FLAT")
            metric_type: Distance metric (default: "L2", options: "L2", "IP", "COSINE")
            params: Index parameters (e.g., {"nlist": 1024} for IVF_FLAT)
            index_name: Optional name for the index

        Returns:
            True if index created successfully, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return False

            # Default parameters for common index types
            if params is None:
                if index_type == "IVF_FLAT":
                    params = {"nlist": 1024}
                elif index_type == "HNSW":
                    params = {"M": 16, "efConstruction": 200}
                elif index_type == "FLAT":
                    params = {}

            index_params = {
                "metric_type": metric_type,
                "index_type": index_type,
                "params": params,
            }

            collection.create_index(
                field_name=field_name, index_params=index_params, index_name=index_name
            )
            logger.info(
                f"Created index on '{field_name}' in '{collection_name}' (type: {index_type}, metric: {metric_type})"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error creating index on '{field_name}' in '{collection_name}': {e}",
                exc_info=True,
            )
            return False

    def load_collection(self, collection_name: str) -> bool:
        """
        Load a collection into memory.

        Args:
            collection_name: Name of the collection

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return False

            collection.load()
            logger.info(f"Loaded collection '{collection_name}' into memory")
            return True
        except Exception as e:
            logger.error(
                f"Error loading collection '{collection_name}': {e}", exc_info=True
            )
            return False

    def release_collection(self, collection_name: str) -> bool:
        """
        Release a collection from memory.

        Args:
            collection_name: Name of the collection

        Returns:
            True if released successfully, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return False

            collection.release()
            logger.info(f"Released collection '{collection_name}' from memory")
            return True
        except Exception as e:
            logger.error(
                f"Error releasing collection '{collection_name}': {e}", exc_info=True
            )
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection information.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information if successful, None otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None

            info = {
                "name": collection_name,
                "description": collection.description,
                "num_entities": collection.num_entities,
                "schema": {
                    "fields": [
                        {
                            "name": field.name,
                            "type": str(field.dtype),
                            "is_primary": field.is_primary,
                            "auto_id": field.auto_id,
                        }
                        for field in collection.schema.fields
                    ]
                },
                "indexes": [
                    {
                        "field_name": idx.field_name,
                        "index_type": idx.params.get("index_type", "unknown"),
                        "metric_type": idx.params.get("metric_type", "unknown"),
                    }
                    for idx in collection.indexes
                ],
            }

            return info
        except Exception as e:
            logger.error(
                f"Error getting collection info for '{collection_name}': {e}",
                exc_info=True,
            )
            return None

    def list_collections(self) -> List[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        try:
            return utility.list_collections()
        except Exception as e:
            logger.error(f"Error listing collections: {e}", exc_info=True)
            return []

    def get_collection_stats(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection statistics.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection statistics if successful, None otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None

            stats = {
                "num_entities": collection.num_entities,
                "is_empty": collection.is_empty,
            }

            return stats
        except Exception as e:
            logger.error(
                f"Error getting collection stats for '{collection_name}': {e}",
                exc_info=True,
            )
            return None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

