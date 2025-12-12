"""Collection management API routes."""
from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import List

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


def get_vector_store(database: str = None) -> MilvusVectorStore:
    """Dependency to get vector store."""
    settings = get_settings()
    db_name = database or settings.milvus_database
    return MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password,
        database=db_name
    )


def get_database_from_query(database: str = None) -> str:
    """Get database name from query parameter or default."""
    if database:
        return database
    settings = get_settings()
    return settings.milvus_database


def get_vector_store_with_database(database: str = None) -> MilvusVectorStore:
    """Dependency to get vector store with database parameter."""
    db_name = get_database_from_query(database)
    return get_vector_store(db_name)


@router.get("")
async def list_collections(
    database: str = None,
    vector_store: MilvusVectorStore = Depends(get_vector_store_with_database)
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
            db_name=vector_store.database
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
                
                # Get embedding dimension from schema
                embedding_dim = None
                try:
                    schema = collection.schema
                    for field in schema.fields:
                        if field.name == "embedding":
                            embedding_dim = field.params.get("dim")
                            break
                except Exception as e:
                    logger.warning(f"Failed to get embedding dim for {name}: {e}")
                
                # Get document count (approximate)
                stats = {
                    "name": name,
                    "document_count": 0,  # Milvus doesn't directly track document count
                    "chunk_count": collection.num_entities,
                    "embedding_dim": embedding_dim,
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
                    "embedding_dim": None,
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
    database: str = Form(None)
):
    """Create a new collection."""
    # Get database name from form parameter or default
    if database:
        db_name = database
    else:
        settings = get_settings()
        db_name = settings.milvus_database
    
    # Create vector store with the correct database
    vector_store = get_vector_store(db_name)
    
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
            db_name=vector_store.database
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
            FieldSchema(
                name="document_id",
                dtype=DataType.VARCHAR,
                max_length=1024
            ),
            FieldSchema(
                name="file_path",
                dtype=DataType.VARCHAR,
                max_length=2048
            ),
            FieldSchema(
                name="metadata",
                dtype=DataType.VARCHAR,
                max_length=4096  # JSON string for location and other metadata
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
    database: str = None,
    vector_store: MilvusVectorStore = Depends(get_vector_store_with_database)
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
            db_name=vector_store.database
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

