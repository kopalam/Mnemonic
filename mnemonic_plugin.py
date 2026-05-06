"""Mnemonic memory plugin for Hermes Agent.

Self-hosted memory system with BM25 keyword search and vector search.

Installation:
    pip install mnemonic

Hermes will auto-discover this plugin via entry_points.
Configure via:
    1. Environment variables:
       MNEMONIC_API_URL=http://localhost:8010
       MNEMONIC_NAMESPACE=hermes:boss:hnoe:*

    2. Or $HERMES_HOME/mnemonic.json:
       {
         "api_url": "http://localhost:8010",
         "namespace": "hermes:boss:hnoe:*"
       }

    3. Or config.yaml:
       memory:
         provider: mnemonic
         memory_enabled: true
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class MemoryProvider:
    """Mnemonic memory provider for Hermes Agent.

    Implements the MemoryProvider interface expected by Hermes.
    """

    def __init__(self):
        """Initialize provider with config from env vars or mnemonic.json."""
        from pathlib import Path

        # Load config
        self.api_url = os.environ.get("MNEMONIC_API_URL", "http://localhost:8010")
        self.namespace = os.environ.get("MNEMONIC_NAMESPACE", "hermes:boss:hnoe:*")

        # Try mnemonic.json override
        hermes_home = os.environ.get("HERMES_HOME", Path.home() / ".hermes")
        config_path = Path(hermes_home) / "mnemonic.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                    self.api_url = cfg.get("api_url", self.api_url)
                    self.namespace = cfg.get("namespace", self.namespace)
            except Exception as e:
                logger.warning(f"Failed to load mnemonic.json: {e}")

        self._client = httpx.Client(timeout=30.0)
        self._async_client = httpx.AsyncClient(timeout=30.0)

        # Circuit breaker
        self._failures = 0
        self._breaker_threshold = 5
        self._breaker_cooldown = 120
        self._breaker_until = 0

        logger.info(f"Mnemonic initialized: api_url={self.api_url}, namespace={self.namespace}")

    def _check_breaker(self) -> bool:
        """Check if circuit breaker is open."""
        if self._failures >= self._breaker_threshold:
            if time.time() < self._breaker_until:
                return True  # Breaker open
            # Reset after cooldown
            self._failures = 0
        return False

    def _record_failure(self):
        """Record failure for circuit breaker."""
        self._failures += 1
        if self._failures >= self._breaker_threshold:
            self._breaker_until = time.time() + self._breaker_cooldown
            logger.warning(f"Circuit breaker opened for {self._breaker_cooldown}s")

    def _reset_breaker(self):
        """Reset circuit breaker on success."""
        self._failures = 0

    # --- MemoryProvider Interface ---

    def add(self, content: str, user_id: str = None, metadata: dict = None) -> dict:
        """Add a memory."""
        if self._check_breaker():
            return {"error": "Circuit breaker open"}

        try:
            payload = {
                "content": content,
                "namespace": self.namespace,
                "user_id": user_id,
                "metadata": metadata or {},
            }
            resp = self._client.post(f"{self.api_url}/memories", json=payload)
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json()
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to add memory: {e}")
            return {"error": str(e)}

    def search(self, query: str, limit: int = 5, mode: str = "keyword") -> List[dict]:
        """Search memories."""
        if self._check_breaker():
            return []

        try:
            params = {
                "query": query,
                "namespace": self.namespace,
                "limit": limit,
                "mode": mode,
            }
            resp = self._client.get(f"{self.api_url}/memories/search", params=params)
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json().get("results", [])
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to search memories: {e}")
            return []

    def get(self, memory_id: str) -> Optional[dict]:
        """Get a specific memory."""
        if self._check_breaker():
            return None

        try:
            resp = self._client.get(f"{self.api_url}/memories/{memory_id}")
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json()
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to get memory: {e}")
            return None

    def update(self, memory_id: str, content: str = None, metadata: dict = None) -> dict:
        """Update a memory."""
        if self._check_breaker():
            return {"error": "Circuit breaker open"}

        try:
            payload = {"namespace": self.namespace}
            if content:
                payload["content"] = content
            if metadata:
                payload["metadata"] = metadata

            resp = self._client.patch(f"{self.api_url}/memories/{memory_id}", json=payload)
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json()
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to update memory: {e}")
            return {"error": str(e)}

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if self._check_breaker():
            return False

        try:
            resp = self._client.delete(
                f"{self.api_url}/memories/{memory_id}",
                params={"namespace": self.namespace}
            )
            resp.raise_for_status()
            self._reset_breaker()
            return True
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to delete memory: {e}")
            return False

    def list_all(self, limit: int = 100) -> List[dict]:
        """List all memories."""
        if self._check_breaker():
            return []

        try:
            params = {"namespace": self.namespace, "limit": limit}
            resp = self._client.get(f"{self.api_url}/memories", params=params)
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json().get("memories", [])
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to list memories: {e}")
            return []

    # --- Async variants for Hermes async operations ---

    async def async_add(self, content: str, user_id: str = None, metadata: dict = None) -> dict:
        """Async add memory."""
        if self._check_breaker():
            return {"error": "Circuit breaker open"}

        try:
            payload = {
                "content": content,
                "namespace": self.namespace,
                "user_id": user_id,
                "metadata": metadata or {},
            }
            resp = await self._async_client.post(f"{self.api_url}/memories", json=payload)
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json()
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to async add memory: {e}")
            return {"error": str(e)}

    async def async_search(self, query: str, limit: int = 5, mode: str = "keyword") -> List[dict]:
        """Async search memories."""
        if self._check_breaker():
            return []

        try:
            params = {
                "query": query,
                "namespace": self.namespace,
                "limit": limit,
                "mode": mode,
            }
            resp = await self._async_client.get(f"{self.api_url}/memories/search", params=params)
            resp.raise_for_status()
            self._reset_breaker()
            return resp.json().get("results", [])
        except Exception as e:
            self._record_failure()
            logger.error(f"Failed to async search memories: {e}")
            return []


# Import time for circuit breaker
import time