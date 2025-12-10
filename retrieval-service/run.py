"""Run the retrieval service."""
import uvicorn
import os

if __name__ == "__main__":
    # Only enable reload in development (when RELOAD env var is set)
    # In production, disable reload to prevent service interruptions
    enable_reload = os.getenv("RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=enable_reload,
        reload_excludes=["logs/*", "*.log", "__pycache__/*", "*.pyc"],  # Exclude logs and cache from reload
        timeout_keep_alive=75,  # Increase keep-alive timeout
        timeout_graceful_shutdown=30,  # Graceful shutdown timeout
        limit_concurrency=100,  # Limit concurrent connections
        backlog=2048  # Connection backlog
    )

