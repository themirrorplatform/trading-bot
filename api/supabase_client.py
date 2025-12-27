"""Supabase client for Trading Bot API."""
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SupabaseClient:
    """Wrapper for Supabase client with RLS auth."""
    
    def __init__(self):
        """Initialize Supabase client."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")  # Service role key for server-side
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        self.client: Client = create_client(url, key)
        
    def insert_decision(self, decision: dict) -> dict:
        """Insert decision event into decisions table."""
        result = self.client.table("decisions").insert(decision).execute()
        return result.data[0] if result.data else {}
    
    def insert_position(self, position: dict) -> dict:
        """Insert or update position into positions table."""
        # Upsert: update if exists, insert if new
        result = self.client.table("positions").upsert(position).execute()
        return result.data[0] if result.data else {}
    
    def insert_readiness(self, readiness: dict) -> dict:
        """Insert readiness snapshot."""
        result = self.client.table("readiness_snapshots").insert(readiness).execute()
        return result.data[0] if result.data else {}
    
    def insert_error(self, error: dict) -> dict:
        """Insert execution error."""
        result = self.client.table("execution_errors").insert(error).execute()
        return result.data[0] if result.data else {}
    
    def insert_status(self, status: dict) -> dict:
        """Insert bot status update."""
        result = self.client.table("bot_status").insert(status).execute()
        return result.data[0] if result.data else {}
    
    def insert_learning_record(self, learning: dict) -> dict:
        """Insert learning record."""
        result = self.client.table("learning_records").insert(learning).execute()
        return result.data[0] if result.data else {}
    
    def get_latest_decisions(self, limit: int = 50, contract: Optional[str] = None) -> list:
        """Fetch latest decisions."""
        query = self.client.table("decisions").select("*").order("timestamp", desc=True).limit(limit)
        if contract:
            query = query.eq("contract", contract)
        result = query.execute()
        return result.data if result.data else []
    
    def get_open_positions(self, contract: Optional[str] = None) -> list:
        """Fetch open positions."""
        query = self.client.table("positions").select("*").eq("status", "OPEN")
        if contract:
            query = query.eq("contract", contract)
        result = query.execute()
        return result.data if result.data else []
    
    def get_latest_readiness(self, contract: str) -> Optional[dict]:
        """Fetch latest readiness snapshot for contract."""
        result = (
            self.client.table("readiness_snapshots")
            .select("*")
            .eq("contract", contract)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    def get_latest_status(self) -> Optional[dict]:
        """Fetch latest bot status."""
        result = (
            self.client.table("bot_status")
            .select("*")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None


# Singleton instance
_client: Optional[SupabaseClient] = None

def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client singleton."""
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client
