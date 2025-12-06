"""Test script to verify API routes."""
import sys
import asyncio
from fastapi.testclient import TestClient

try:
    from app.main import app
    
    client = TestClient(app)
    
    # List all routes
    print("Available routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods)
            print(f"  {methods:10} {route.path}")
    
    # Test health endpoint
    print("\nTesting /health endpoint:")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    
    # Test search/debug endpoint (should return 422 for missing body, but route should exist)
    print("\nTesting /api/v1/retrieval/search/debug endpoint:")
    response = client.post("/api/v1/retrieval/search/debug", json={})
    print(f"  Status: {response.status_code}")
    if response.status_code == 404:
        print("  ERROR: Route not found!")
    elif response.status_code == 422:
        print("  OK: Route exists (422 is expected for invalid request)")
    else:
        print(f"  Response: {response.text[:200]}")
        
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

