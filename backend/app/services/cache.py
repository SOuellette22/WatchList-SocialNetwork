import threading
import time
from typing import Any

class TTLCache:
    """Thread-safe in-process cache with per-entry time-to-live."""

    def __init__(self, ttl_seconds: int, max_size: int = 1000) -> None:
        self._tll = ttl_seconds
        self._max_size = max_size
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Any | None:
        
        with self._lock:
            entry = self._store.get(key)
            
            if entry is None:
                return None
            
            value, expiry = entry
            
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            
            return value
        
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max_size and key not in self._store:
                
                oldest = min(self._store, key = lambda k: self._store[k][1])
                
                del self._store[oldest]
                
            self._store[key] = (value, time.monotonic() + self._tll)