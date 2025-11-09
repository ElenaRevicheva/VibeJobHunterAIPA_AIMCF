"""Rate limiting for API calls"""
import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for API calls"""
    
    def __init__(self, max_calls: int, period: float):
        """
        Args:
            max_calls: Maximum calls allowed per period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until a call is allowed"""
        async with self._lock:
            now = time.time()
            
            # Remove calls outside the current period
            while self.calls and self.calls[0] <= now - self.period:
                self.calls.popleft()
            
            # If at limit, wait
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.period - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            # Record this call
            self.calls.append(now)
    
    def sync_acquire(self):
        """Synchronous version of acquire"""
        now = time.time()
        
        # Remove calls outside the current period
        while self.calls and self.calls[0] <= now - self.period:
            self.calls.popleft()
        
        # If at limit, wait
        if len(self.calls) >= self.max_calls:
            sleep_time = self.calls[0] + self.period - now
            if sleep_time > 0:
                time.sleep(sleep_time)
                return self.sync_acquire()
        
        # Record this call
        self.calls.append(now)


class APICallTracker:
    """Track API call costs and usage"""
    
    def __init__(self):
        self.total_calls = 0
        self.total_tokens = 0
        self.estimated_cost = 0.0
        
        # Claude pricing (approximate)
        self.input_cost_per_1m = 3.0  # $3 per 1M input tokens
        self.output_cost_per_1m = 15.0  # $15 per 1M output tokens
    
    def record_call(self, input_tokens: int, output_tokens: int):
        """Record an API call"""
        self.total_calls += 1
        self.total_tokens += input_tokens + output_tokens
        
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_1m
        self.estimated_cost += input_cost + output_cost
    
    def get_stats(self) -> dict:
        """Get usage statistics"""
        return {
            'total_calls': self.total_calls,
            'total_tokens': self.total_tokens,
            'estimated_cost_usd': round(self.estimated_cost, 4),
            'avg_tokens_per_call': round(self.total_tokens / max(self.total_calls, 1), 2)
        }
