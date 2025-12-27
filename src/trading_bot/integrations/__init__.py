"""Supabase publisher for trading bot events."""
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class SupabasePublisher:
    """
    Publishes trading bot events to FastAPI backend → Supabase.
    
    Handles retries and local fallback if API is unreachable.
    """
    
    def __init__(self, api_url: str = "http://localhost:8000", max_retries: int = 3):
        """
        Initialize publisher.
        
        Args:
            api_url: Base URL for API (e.g., "http://localhost:8000" or "https://api.yourbot.com")
            max_retries: Number of retries on failure
        """
        self.api_url = api_url.rstrip("/")
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=10.0)
        self._connected = False
        
    async def _post(self, endpoint: str, data: dict) -> Optional[dict]:
        """
        Post data to API endpoint with retry logic.
        
        Args:
            endpoint: API endpoint (e.g., "/api/decisions")
            data: JSON payload
            
        Returns:
            Response data or None if failed
        """
        url = f"{self.api_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(url, json=data)
                response.raise_for_status()
                self._connected = True
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on {endpoint}: {e.response.status_code} - {e.response.text}")
                if attempt == self.max_retries - 1:
                    self._connected = False
                    return None
            except httpx.RequestError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    self._connected = False
                    return None
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        return None
    
    async def publish_decision(self, decision: dict) -> bool:
        """
        Publish decision event to API.
        
        Args:
            decision: Decision event dict with keys: timestamp, contract, decision, reason_code, signals, belief, market_context
            
        Returns:
            True if successfully published, False otherwise
        """
        result = await self._post("/api/decisions", decision)
        if result:
            logger.info(f"Decision published: {decision.get('contract')} - {decision.get('decision')}")
            return True
        else:
            logger.error(f"Failed to publish decision: {decision.get('contract')}")
            return False
    
    async def publish_position(self, position: dict) -> bool:
        """
        Publish position update to API.
        
        Args:
            position: Position dict with keys: timestamp, contract, action, position_size, entry_price, current_price, unrealized_pnl
            
        Returns:
            True if successfully published
        """
        result = await self._post("/api/positions", position)
        if result:
            logger.info(f"Position published: {position.get('contract')} - {position.get('action')}")
            return True
        else:
            logger.error(f"Failed to publish position: {position.get('contract')}")
            return False
    
    async def publish_readiness(self, readiness: dict) -> bool:
        """
        Publish readiness snapshot to API.
        
        Args:
            readiness: Readiness dict with keys: timestamp, contract, now_et, dte, levels, distances, atr_proxy, data_quality
            
        Returns:
            True if successfully published
        """
        result = await self._post("/api/readiness", readiness)
        if result:
            logger.info(f"Readiness published: {readiness.get('contract')}")
            return True
        else:
            logger.error(f"Failed to publish readiness: {readiness.get('contract')}")
            return False
    
    async def publish_error(self, error: dict) -> bool:
        """
        Publish execution error to API.
        
        Args:
            error: Error dict with keys: timestamp, contract, error_type, message, severity
            
        Returns:
            True if successfully published
        """
        result = await self._post("/api/errors", error)
        if result:
            logger.warning(f"Error published: {error.get('error_type')}")
            return True
        else:
            logger.error(f"Failed to publish error: {error.get('error_type')}")
            return False
    
    async def publish_status(self, status: dict) -> bool:
        """
        Publish bot status to API.
        
        Args:
            status: Status dict with keys: timestamp, adapter, mode, connected, account_equity, execution_enabled, session_open
            
        Returns:
            True if successfully published
        """
        result = await self._post("/api/status", status)
        if result:
            logger.info(f"Status published: {status.get('adapter')}/{status.get('mode')}")
            return True
        else:
            logger.error(f"Failed to publish status")
            return False
    
    async def publish_learning(self, learning: dict) -> bool:
        """
        Publish learning record to API.
        
        Args:
            learning: Learning dict with keys: timestamp, contract, trade_id, signal_correlations, pnl, duration_bars
            
        Returns:
            True if successfully published
        """
        result = await self._post("/api/learning", learning)
        if result:
            logger.info(f"Learning record published: trade {learning.get('trade_id')}")
            return True
        else:
            logger.error(f"Failed to publish learning record")
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if API is reachable."""
        return self._connected
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Synchronous wrapper for non-async contexts
class SupabasePublisherSync:
    """Synchronous wrapper for SupabasePublisher."""
    
    def __init__(self, api_url: str = "http://localhost:8000", max_retries: int = 3):
        self.publisher = SupabasePublisher(api_url=api_url, max_retries=max_retries)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def publish_decision(self, decision: dict) -> bool:
        return self.loop.run_until_complete(self.publisher.publish_decision(decision))
    
    def publish_position(self, position: dict) -> bool:
        return self.loop.run_until_complete(self.publisher.publish_position(position))
    
    def publish_readiness(self, readiness: dict) -> bool:
        return self.loop.run_until_complete(self.publisher.publish_readiness(readiness))
    
    def publish_error(self, error: dict) -> bool:
        return self.loop.run_until_complete(self.publisher.publish_error(error))
    
    def publish_status(self, status: dict) -> bool:
        return self.loop.run_until_complete(self.publisher.publish_status(status))
    
    def publish_learning(self, learning: dict) -> bool:
        return self.loop.run_until_complete(self.publisher.publish_learning(learning))
    
    @property
    def is_connected(self) -> bool:
        return self.publisher.is_connected
    
    def close(self):
        self.loop.run_until_complete(self.publisher.close())
        self.loop.close()
