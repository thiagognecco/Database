"""Cache and rate limiting for AI service."""
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Cache file for persistence across restarts
CACHE_FILE = Path(__file__).parent / ".." / "dados" / "ai_cache.json"


class AICache:
    """In-memory cache with persistent storage for AI analysis results."""

    def __init__(self):
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.load_from_disk()

    def load_from_disk(self):
        """Load cache from JSON file if it exists."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.memory_cache = json.load(f)
                logger.info(f"AI cache loaded: {len(self.memory_cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load AI cache: {e}")

    def save_to_disk(self):
        """Persist cache to JSON file."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.memory_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save AI cache: {e}")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value by key (usually URL)."""
        if key in self.memory_cache:
            return self.memory_cache[key]
        return None

    def set(self, key: str, value: Dict[str, Any]):
        """Cache a value and persist to disk."""
        self.memory_cache[key] = {
            **value,
            "cached_at": datetime.utcnow().isoformat(),
            "hit_count": self.memory_cache.get(key, {}).get("hit_count", 0) + 1
        }
        self.save_to_disk()

    def clear(self):
        """Clear all cache."""
        self.memory_cache.clear()
        self.save_to_disk()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(entry.get("hit_count", 0) for entry in self.memory_cache.values())
        return {
            "entries": len(self.memory_cache),
            "total_hits": total_hits,
            "avg_hits_per_entry": total_hits / len(self.memory_cache) if self.memory_cache else 0
        }


class RateLimiter:
    """Rate limiting for API calls."""

    def __init__(self, max_calls: int = 20, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.call_times: list = []

    def is_allowed(self) -> bool:
        """Check if a call is allowed within rate limit."""
        now = time.time()
        # Remove old calls outside the window
        self.call_times = [t for t in self.call_times if now - t < self.window_seconds]

        if len(self.call_times) < self.max_calls:
            self.call_times.append(now)
            return True

        return False

    def wait_if_needed(self) -> float:
        """Return seconds to wait if rate limited, or 0 if allowed."""
        if self.is_allowed():
            return 0

        # Wait until oldest call is outside window
        oldest = self.call_times[0]
        wait_time = max(0, (oldest + self.window_seconds) - time.time())
        return wait_time

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        now = time.time()
        self.call_times = [t for t in self.call_times if now - t < self.window_seconds]

        return {
            "calls_used": len(self.call_times),
            "calls_allowed": self.max_calls,
            "window_seconds": self.window_seconds,
            "available": self.max_calls - len(self.call_times)
        }


# Global instances
ai_cache = AICache()
rate_limiter = RateLimiter(max_calls=20, window_seconds=60)  # 20 calls per minute
