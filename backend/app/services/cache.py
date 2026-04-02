import threading
import time
from typing import Any

class TTLCache:
    """Thread-safe in-process cache with per-entry time-to-live."""

    def __init__(self, ttl_seconds: int, max_size: int = 1000) -> None:
        self._tll = ttl_seconds                         # the seconds that the entry should last
        self._max_size = max_size
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()                   # sets up the thread safe guards
        
    def get(self, key: str) -> Any | None:
        
        # checks if the data structure is being used
        with self._lock:
            
            # gets the given key from the store
            entry = self._store.get(key)
            
            # if the key is not in the store return None
            if entry is None:
                return None
            
            # Entry is a tuple so get the value and the expire time
            value, expiry = entry
            
            # Checks if the expire time passed if it has remove it from the store and return None
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            
            # Return the value if all checks pass
            return value
        
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            
            # If the length of the store is the max size remove the oldest things from the cache
            if len(self._store) >= self._max_size and key not in self._store:
                
                oldest = min(self._store, key = lambda k: self._store[k][1])
                
                del self._store[oldest]
                
            # Add the new time to the store
            self._store[key] = (value, time.monotonic() + self._tll)