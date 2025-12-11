"""
Database Query Cache for ParagonOCR 2.0

Implements LRU cache for database query results to improve performance.

Author: ParagonOCR Team
Version: 2.0
"""

import hashlib
import json
import logging
from typing import Any, Callable, Dict, Optional, Tuple
from collections import OrderedDict
from functools import wraps

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.
    
    Attributes:
        max_size: Maximum number of items in cache
        cache: OrderedDict storing cached items
    """
    
    def __init__(self, max_size: int = 200) -> None:
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to cache (default: 200)
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing item
            self.cache.move_to_end(key)
        else:
            # Check if cache is full
            if len(self.cache) >= self.max_size:
                # Remove least recently used (first item)
                self.cache.popitem(last=False)
        
        self.cache[key] = value
    
    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 2)
        }


# Global cache instance
_query_cache = LRUCache(max_size=200)


def cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    # Create a hashable representation
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    
    # Convert to JSON string and hash
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached_query(max_age_seconds: Optional[int] = None):
    """
    Decorator for caching database query results.
    
    Args:
        max_age_seconds: Optional maximum age of cached results in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = _query_cache.get(key)
            if cached_result is not None:
                # Check age if max_age specified
                if max_age_seconds is None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
                else:
                    # TODO: Implement age checking if needed
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Store in cache
            _query_cache.set(key, result)
            
            return result
        
        return wrapper
    return decorator


def clear_query_cache() -> None:
    """Clear all cached query results."""
    _query_cache.clear()
    logger.info("Query cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get query cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    return _query_cache.get_stats()

