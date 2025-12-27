from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
import time

class ConnectionState:
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    READY = "READY"
    ERROR = "ERROR"

@dataclass
class IBKRConnectionManager:
    host: str = "127.0.0.1"
    port: int = 7497  # Paper trading (7496 = live)
    client_id: int = 1

    state: str = ConnectionState.DISCONNECTED
    retries: int = 0
    max_retries: int = 5
    last_heartbeat: Optional[datetime] = None
    heartbeat_timeout_seconds: int = 30
    error_message: str = ""
    
    _ib: Any = None
    _retry_backoff: list[int] = field(default_factory=lambda: [2, 4, 8, 16, 32])

    def connect(self) -> bool:
        """Attempt to connect to TWS/IB Gateway."""
        self.state = ConnectionState.CONNECTING
        self.retries = 0
        try:
            import ib_insync
            self._ib = ib_insync.IB()
            self._ib.connect(self.host, self.port, clientId=self.client_id, readonly=False)
            self.state = ConnectionState.CONNECTED
            self.last_heartbeat = datetime.utcnow()
            self.error_message = ""
            return True
        except ImportError:
            # ib_insync not available; allow scaffolding mode
            self.state = ConnectionState.READY  # No-op mode
            self.error_message = "ib_insync not installed; observation mode"
            return True
        except Exception as e:
            self.state = ConnectionState.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> None:
        """Disconnect from TWS."""
        if self._ib:
            try:
                self._ib.disconnect()
            except Exception:
                pass
        self._ib = None
        self.state = ConnectionState.DISCONNECTED
        self.error_message = ""

    def reconnect(self) -> bool:
        """Reconnect with exponential backoff."""
        if self.retries >= self.max_retries:
            self.state = ConnectionState.ERROR
            self.error_message = f"Max retries ({self.max_retries}) exceeded"
            return False
        
        backoff = self._retry_backoff[min(self.retries, len(self._retry_backoff) - 1)]
        time.sleep(backoff)
        self.retries += 1
        return self.connect()

    def ensure(self) -> bool:
        """Ensure connected; reconnect if needed."""
        if self.state == ConnectionState.READY:
            return True  # No-op/scaffolding mode
        
        if self.state == ConnectionState.CONNECTED:
            # Check heartbeat
            if self.last_heartbeat:
                age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
                if age > self.heartbeat_timeout_seconds:
                    self.state = ConnectionState.ERROR
                    return self.reconnect()
            return True
        
        if self.state in (ConnectionState.ERROR, ConnectionState.DISCONNECTED):
            return self.reconnect()
        
        return False

    def heartbeat(self) -> None:
        """Update heartbeat timestamp (call periodically to ensure connection alive)."""
        self.last_heartbeat = datetime.utcnow()

    def is_connected(self) -> bool:
        """Quick check without reconnect attempt."""
        return self.state in (ConnectionState.CONNECTED, ConnectionState.READY)
