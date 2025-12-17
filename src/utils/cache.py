"""Response caching to save API costs"""
import json
import hashlib
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timedelta


class ResponseCache:
    """Cache AI responses to reduce API calls"""
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        """
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _generate_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model"""
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[str]:
        """
        Get cached response if available and not expired
        
        Args:
            prompt: The prompt text
            model: Model name
            
        Returns:
            Cached response or None
        """
        key = self._generate_key(prompt, model)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if expired
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                cache_file.unlink()  # Delete expired cache
                return None
            
            return data['response']
        
        except Exception:
            return None
    
    def set(self, prompt: str, model: str, response: str):
        """
        Cache a response
        
        Args:
            prompt: The prompt text
            model: Model name
            response: The AI response to cache
        """
        key = self._generate_key(prompt, model)
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'prompt_hash': key,
            'response': response
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Silently fail on cache write errors
    
    def set_data(self, cache_key: str, data: Any):
        """
        Cache arbitrary data by key (for company research, etc.)
        
        Args:
            cache_key: Unique key for this cache entry
            data: Any JSON-serializable data
        """
        key_hash = hashlib.sha256(cache_key.encode()).hexdigest()
        cache_file = self.cache_dir / f"{key_hash}.json"
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'cache_key': cache_key,
            'data': data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
        except Exception:
            pass  # Silently fail on cache write errors
    
    def get_data(self, cache_key: str) -> Optional[Any]:
        """
        Get cached data by key
        
        Args:
            cache_key: Unique key for this cache entry
            
        Returns:
            Cached data or None
        """
        key_hash = hashlib.sha256(cache_key.encode()).hexdigest()
        cache_file = self.cache_dir / f"{key_hash}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if expired
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                cache_file.unlink()
                return None
            
            return cache_data.get('data')
        except Exception:
            return None
    
    def clear(self):
        """Clear all cached responses"""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception:
                pass
    
    def clear_expired(self):
        """Remove only expired cache entries"""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                cached_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cached_time > self.ttl:
                    cache_file.unlink()
            except Exception:
                pass
