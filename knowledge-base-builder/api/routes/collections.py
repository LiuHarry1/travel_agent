"""Collection management API routes."""
from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import List

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


def get_vector_store() -> MilvusVectorStore:
    """Dependency to get vector store."""
    settings = get_settings()
    return MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password
    )


@router.get("")
async def list_collections(
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """List all collections in Milvus."""
    connection_alias = "default"
    try:
        # Connect to Milvus using default alias
        from pymilvus import connections
        
        # Disconnect if already connected to avoid conflicts
        try:
            connections.disconnect(connection_alias)
        except:
            pass
        
        connections.connect(
            alias=connection_alias,
            host=vector_store.host,
            port=vector_store.port,
            user=vector_store.user if vector_store.user else None,
            password=vector_store.password if vector_store.password else None,
        )
        
        # Import here to avoid circular dependency
        from pymilvus import utility
        
        # Use the connection alias explicitly
        collections = utility.list_collections(using=connection_alias)
        
        # Get stats for each collection
        collection_info = []
        for name in collections:
            try:
                from pymilvus import Collection
                collection = Collection(name, using=connection_alias)
                collection.load()
                
                # Get document count (approximate)
                stats = {
                    "name": name,
                    "document_count": 0,  # Milvus doesn't directly track document count
                    "chunk_count": collection.num_entities,
                    "created_at": "",  # Milvus doesn't store creation time
                    "last_updated": ""  # Milvus doesn't store update time
                }
                collection_info.append(stats)
            except Exception as e:
                logger.warning(f"Failed to get stats for collection {name}: {e}")
                collection_info.append({
                    "name": name,
                    "document_count": 0,
                    "chunk_count": 0,
                    "created_at": "",
                    "last_updated": ""
                })
        
        return JSONResponse(
            status_code=200,
            content={"collections": collection_info}
        )
    except Exception as e:
        logger.error(f"Failed to list collections: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from pymilvus import connections
            connections.disconnect(connection_alias)
        except:
            pass


@router.post("")
async def create_collection(
    name: str = Form(...),
    embedding_dim: int = Form(1536),
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """Create a new collection."""
    connection_alias = "default"
    try:
        from pymilvus import connections
        
        # Disconnect if already connected to avoid conflicts
        try:
            connections.disconnect(connection_alias)
        except:
            pass
        
        connections.connect(
            alias=connection_alias,
            host=vector_store.host,
            port=vector_store.port,
            user=vector_store.user if vector_store.user else None,
            password=vector_store.password if vector_store.password else None,
        )
        
        from pymilvus import utility, Collection, CollectionSchema, FieldSchema, DataType
        
        # Check if collection already exists
        if utility.has_collection(name, using=connection_alias):
            raise HTTPException(
                status_code=400,
                detail=f"Collection '{name}' already exists"
            )
        
        # Create collection schema
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True
            ),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=65535
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=embedding_dim
            ),
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description=f"Knowledge base collection: {name}"
        )
        
        collection = Collection(name=name, schema=schema, using=connection_alias)
        
        # Create index
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index("embedding", index_params)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Collection '{name}' created successfully",
                "collection_name": name
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create collection: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from pymilvus import connections
            connections.disconnect(connection_alias)
        except:
            pass


@router.delete("/{name}")
async def delete_collection(
    name: str,
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """Delete a collection."""
    connection_alias = "default"
    try:
        from pymilvus import connections
        
        # Disconnect if already connected to avoid conflicts
        try:
            connections.disconnect(connection_alias)
        except:
            pass
        
        connections.connect(
            alias=connection_alias,
            host=vector_store.host,
            port=vector_store.port,
            user=vector_store.user if vector_store.user else None,
            password=vector_store.password if vector_store.password else None,
        )
        
        from pymilvus import utility
        
        if not utility.has_collection(name, using=connection_alias):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{name}' not found"
            )
        
        utility.drop_collection(name, using=connection_alias)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Collection '{name}' deleted successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete collection: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from pymilvus import connections
            connections.disconnect(connection_alias)
        except:
            pass

