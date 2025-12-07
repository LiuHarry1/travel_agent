"""Main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import os
from app.api import router
from app.infrastructure.config.settings import settings
from app.infrastructure.vector_store.connection_pool import milvus_connection_pool
from app.services.service_factory import clear_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Load .env file manually to ensure all environment variables are available
try:
    from dotenv import load_dotenv
    # Try to load .env from the project root (retrieval-service directory)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env file from {env_path}")
    else:
        # Also try current directory
        load_dotenv()
        logger.info("Loaded .env file from current directory")
except ImportError:
    # python-dotenv not installed, try to manually read .env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        logger.info(f"python-dotenv not installed, attempting to load .env manually from {env_path}")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value and key not in os.environ:
                        os.environ[key] = value
        logger.info("Manually loaded .env file")
except Exception as e:
    logger.warning(f"Failed to load .env file: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and shutdown."""
    # Startup
    logger.info("Starting retrieval service...")
    yield
    # Shutdown
    logger.info("Shutting down retrieval service...")
    try:
        # Clear service cache
        clear_cache()
        logger.info("Cleared service cache")
    except Exception as e:
        logger.error(f"Error clearing service cache: {e}", exc_info=True)
    
    try:
        # Close all Milvus connections
        milvus_connection_pool.close_all()
        logger.info("Closed all Milvus connections")
    except Exception as e:
        logger.error(f"Error closing Milvus connections: {e}", exc_info=True)
    
    logger.info("Shutdown complete")


app = FastAPI(
    title="Retrieval Service",
    description="RAG retrieval service with multi-embedding models and re-ranking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

