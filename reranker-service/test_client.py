"""Test client for reranker service."""
import requests
import json

def test_rerank():
    """Test rerank endpoint."""
    url = "http://localhost:8009/api/v1/rerank"
    
    payload = {
        "query": "What is machine learning?",
        "documents": [
            "Machine learning is a subset of artificial intelligence.",
            "Python is a programming language.",
            "Deep learning uses neural networks for machine learning.",
            "JavaScript is used for web development.",
            "Machine learning algorithms learn from data."
        ],
        "top_k": 3
    }
    
    print("Testing rerank endpoint...")
    print(f"Query: {payload['query']}")
    print(f"Documents: {len(payload['documents'])}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        print("Response:")
        print(json.dumps(result, indent=2))
        print()
        
        print("Top results:")
        for i, res in enumerate(result["results"], 1):
            idx = res["index"]
            score = res["relevance_score"]
            doc = payload["documents"][idx]
            print(f"{i}. Score: {score:.4f}")
            print(f"   Document: {doc[:80]}...")
            print()
            
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")


if __name__ == "__main__":
    test_rerank()

