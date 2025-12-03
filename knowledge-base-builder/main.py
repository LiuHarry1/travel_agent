"""FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from api.routes import indexing, collections, config
from config.settings import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Knowledge Base Builder API",
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

# Register routes
app.include_router(indexing.router)
app.include_router(collections.router)
app.include_router(config.router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Knowledge Base Builder API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )

