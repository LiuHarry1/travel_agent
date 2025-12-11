"""FastAPI application entry point."""
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import indexing, collections, config, sources, databases
from config.settings import get_settings
from utils.logger import setup_logging, get_logger

# Setup logging (before getting settings to avoid circular dependency)
setup_logging(
    log_level=None,  # Will use default INFO level
    log_dir="logs",
    log_file="kb-builder-service.log",
    console_output=True,
    file_output=True
)
logger = get_logger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="KB Builder Service API",
    version="1.0.0",
    description="API for indexing documents into vector knowledge base"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    # Convert errors to a serializable format
    errors = []
    for error in exc.errors():
        serializable_error = {
            "type": str(error.get("type", "unknown")),
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "Unknown error")),
            "input": str(error.get("input", "")) if error.get("input") is not None else None
        }
        # Safely handle ctx if it exists
        if "ctx" in error:
            try:
                ctx = error["ctx"]
                serializable_error["ctx"] = {
                    k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                    for k, v in ctx.items()
                }
            except Exception:
                serializable_error["ctx"] = {"error": "Unable to serialize context"}
        errors.append(serializable_error)
    
    logger.error(f"Validation error: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors
        }
    )

# Mount static files (for images and source files)
static_dir = Path(settings.static_dir)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Mounted static files from: {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}. Static files will not be served.")

# Register routes
app.include_router(indexing.router)
app.include_router(collections.router)
app.include_router(config.router)
app.include_router(sources.router)
app.include_router(databases.router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "KB Builder Service API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True
    )

