"""Database management API routes."""
from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import List

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/databases", tags=["databases"])


def get_vector_store(database: str = "default") -> MilvusVectorStore:
    """Dependency to get vector store for database operations."""
    settings = get_settings()
    return MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password,
        database=database
    )


@router.get("")
async def list_databases():
    """List all databases in Milvus."""
    connection_alias = "db_list"
    try:
        settings = get_settings()
        from pymilvus import connections, db
        
        # Disconnect if already connected to avoid conflicts
        try:
            connections.disconnect(connection_alias)
        except:
            pass
        
        # Connect to Milvus (using default database to list all databases)
        connections.connect(
            alias=connection_alias,
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user if settings.milvus_user else None,
            password=settings.milvus_password if settings.milvus_password else None,
            db_name="default"
        )
        
        # List all databases
        databases = db.list_database(using=connection_alias)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "databases": databases,
                "current": settings.milvus_database
            }
        )
    except Exception as e:
        logger.error(f"Failed to list databases: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from pymilvus import connections
            connections.disconnect(connection_alias)
        except:
            pass


@router.post("")
async def create_database(
    name: str = Form(...)
):
    """Create a new database."""
    connection_alias = "db_create"
    try:
        settings = get_settings()
        from pymilvus import connections, db
        
        # Disconnect if already connected to avoid conflicts
        try:
            connections.disconnect(connection_alias)
        except:
            pass
        
        # Connect to Milvus
        connections.connect(
            alias=connection_alias,
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user if settings.milvus_user else None,
            password=settings.milvus_password if settings.milvus_password else None,
            db_name="default"
        )
        
        # Create database
        db.create_database(name, using=connection_alias)
        
        logger.info(f"Created database: {name}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Database '{name}' created successfully",
                "database_name": name
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from pymilvus import connections
            connections.disconnect(connection_alias)
        except:
            pass


@router.delete("/{name}")
async def delete_database(
    name: str
):
    """Delete a database."""
    connection_alias = "db_delete"
    try:
        settings = get_settings()
        from pymilvus import connections, db
        
        # Disconnect if already connected to avoid conflicts
        try:
            connections.disconnect(connection_alias)
        except:
            pass
        
        # Connect to Milvus
        connections.connect(
            alias=connection_alias,
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user if settings.milvus_user else None,
            password=settings.milvus_password if settings.milvus_password else None,
            db_name="default"
        )
        
        # Check if database exists
        databases = db.list_database(using=connection_alias)
        if name not in databases:
            raise HTTPException(
                status_code=404,
                detail=f"Database '{name}' not found"
            )
        
        # Prevent deletion of default database
        if name == "default":
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the default database"
            )
        
        # Delete database
        db.drop_database(name, using=connection_alias)
        
        logger.info(f"Deleted database: {name}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Database '{name}' deleted successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from pymilvus import connections
            connections.disconnect(connection_alias)
        except:
            pass

