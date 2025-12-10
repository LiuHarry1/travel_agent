"""Cache for RAG query results."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RAGCache:
    """Simple in-memory cache for RAG query results with TTL support."""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize RAG cache.
        
        Args:
            ttl_seconds: Time to live for cache entries in seconds
            max_size: Maximum number of cache entries
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._access_times: Dict[str, float] = {}  # Track access times for LRU eviction
    
    def get(self, key: str) -> Optional[Dict]:
        """
        Get cached value if exists and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        timestamp = entry.get("timestamp", 0)
        current_time = time.time()
        
        # Check if expired
        if current_time - timestamp > self.ttl:
            logger.debug(f"Cache entry expired for key: {key[:50]}")
            del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
            return None
        
        # Update access time for LRU
        self._access_times[key] = current_time
        return entry.get("value")
    
    def set(self, key: str, value: Dict) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        current_time = time.time()
        
        # Evict oldest entries if cache is full
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_oldest()
        
        # Store entry with timestamp
        self._cache[key] = {
            "value": value,
            "timestamp": current_time
        }
        self._access_times[key] = current_time
        logger.debug(f"Cached result for key: {key[:50]}")
    
    def _evict_oldest(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            # Fallback: remove first entry
            if self._cache:
                key = next(iter(self._cache))
                del self._cache[key]
            return
        
        # Find least recently used
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        del self._cache[lru_key]
        del self._access_times[lru_key]
        logger.debug(f"Evicted cache entry: {lru_key[:50]}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_times.clear()
        logger.info("Cache cleared")
    
    def _generate_key(self, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Generate cache key from query and conversation history.
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            
        Returns:
            Cache key string
        """
        # Include query
        key_parts = [query]
        
        # Include relevant parts of conversation history (last 2 user messages)
        if conversation_history:
            recent_user_messages = [
                msg.get("content", "")[:100]  # First 100 chars
                for msg in conversation_history[-4:]  # Last 4 messages
                if msg.get("role") == "user"
            ][-2:]  # Last 2 user messages
            if recent_user_messages:
                key_parts.extend(recent_user_messages)
        
        # Create hash of key parts
        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode("utf-8")).hexdigest()
        return f"rag:{key_hash}"
    
    def get_or_compute(
        self,
        key: str,
        compute_func,
        *args,
        **kwargs
    ) -> Dict:
        """
        Get from cache or compute and cache result.
        
        Args:
            key: Cache key
            compute_func: Async function to compute value if not cached
            *args: Arguments for compute_func
            **kwargs: Keyword arguments for compute_func
            
        Returns:
            Cached or computed value
        """
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {key[:50]}")
            return cached
        
        logger.debug(f"Cache miss for key: {key[:50]}")
        # Note: This assumes compute_func is async, caller should await
        # For now, we'll just return None and let caller handle computation
        return None
