"""Hermes MemoryProvider adapter for Mnemonic.

This module implements the Hermes MemoryProvider interface,
allowing any Hermes instance to use Mnemonic as its memory backend.
"""

from typing import Any, Optional

import httpx

from mnemonic.schemas import MemoryCreate, Namespace


class MnemonicProvider:
    """Hermes MemoryProvider adapter.
    
    Implements the Hermes MemoryProvider ABC:
    - add(content, metadata) -> memory_id
    - search(query, limit) -> list[Memory]
    - get(memory_id) -> Memory | None
    - delete(memory_id) -> bool
    - update(memory_id, content, metadata) -> Memory | None
    
    Usage in Hermes config.yaml:
        memory:
          provider: mnemonic
          base_url: "http://localhost:8000"
          namespace: "my_client:my_user:my_agent"
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        client_id: str = "default",
        user_id: str = "default",
        agent_id: str = "default",
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.namespace = Namespace(
            client_id=client_id,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        self._headers = {
            "X-Namespace": f"{client_id}:{user_id}:{agent_id}" + (f":{session_id}" if session_id else ""),
            "Content-Type": "application/json",
        }
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=30.0,
        )
    
    async def add(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict:
        """Add a new memory. Returns the created memory object."""
        payload = {
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
        }
        if metadata:
            payload.update(metadata)
        
        response = await self._client.post("/memories", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> list[dict]:
        """Search memories by semantic similarity."""
        payload = {
            "query": query,
            "limit": limit,
            "use_vector": True,
        }
        if memory_type:
            payload["memory_type"] = memory_type
        if min_importance:
            payload["min_importance"] = min_importance
        
        response = await self._client.post("/memories/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get(self, memory_id: str) -> Optional[dict]:
        """Get a memory by ID."""
        response = await self._client.get(f"/memories/{memory_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory (soft delete)."""
        response = await self._client.delete(f"/memories/{memory_id}")
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True
    
    async def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        """Update a memory."""
        payload = {}
        if content is not None:
            payload["content"] = content
        if memory_type is not None:
            payload["memory_type"] = memory_type
        if importance is not None:
            payload["importance"] = importance
        if metadata:
            payload.update(metadata)
        
        response = await self._client.patch(f"/memories/{memory_id}", json=payload)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    async def extract(self, conversation: str) -> list[dict]:
        """Extract and store memories from a conversation."""
        response = await self._client.post(
            "/memories/extract",
            params={"conversation": conversation},
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    # Context manager support
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
