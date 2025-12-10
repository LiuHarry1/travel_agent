"""Main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import os
import logging
from app.api import router
from app.infrastructure.config.settings import settings
from app.infrastructure.vector_store.connection_pool import milvus_connection_pool
from app.services.service_factory import clear_cache
from app.utils.logger import setup_logging, get_logger

# Configure logging before creating logger
log_level_env = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = logging.DEBUG if log_level_env == "DEBUG" else logging.INFO

# Get project root (retrieval-service directory)
_project_root = Path(__file__).parent.parent.resolve()

setup_logging(
    log_level=log_level,
    log_dir=str(_project_root / "logs"),
    log_file="app.log",
    console_output=True,
    file_output=True
)

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

# Add request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests."""
    import time
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    logger.info(
        f"Incoming request: {request.method} {request.url.path} "
        f"from {client_host}, query_params={dict(request.query_params)}"
    )
    try:
        response = await call_next(request)
        elapsed = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} -> {response.status_code} "
            f"(took {elapsed:.2f}s)"
        )
        return response
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} -> {type(e).__name__}: {e} "
            f"(took {elapsed:.2f}s)",
            exc_info=True
        )
        raise

app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if service can access pipeline configs
        from app.infrastructure.config.pipeline_config import pipeline_config_manager
        pipelines = pipeline_config_manager.get_pipelines()
        return {
            "status": "healthy",
            "service": "retrieval-service",
            "pipelines_available": len(pipelines.pipelines) if hasattr(pipelines, 'pipelines') else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "retrieval-service",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

