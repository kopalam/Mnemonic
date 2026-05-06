"""Mnemonic memory plugin — MemoryProvider interface.

Self-hosted memory system with BM25 keyword search and vector search.
API endpoint: http://localhost:8010

Config via environment variables:
  MNEMONIC_API_URL    — Mnemonic API endpoint (default: http://localhost:8010)
  MNEMONIC_NAMESPACE  — Namespace for memory isolation (default: hermes:boss:hnoe:*)

Or via $HERMES_HOME/mnemonic.json.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

logger = logging.getLogger(__name__)

# Circuit breaker: after this many consecutive failures, pause API calls
# for _BREAKER_COOLDOWN_SECS to avoid hammering a down server.
_BREAKER_THRESHOLD = 5
_BREAKER_COOLDOWN_SECS = 120


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load config from env vars, with $HERMES_HOME/mnemonic.json overrides."""
    from hermes_constants import get_hermes_home

    config = {
        "api_url": os.environ.get("MNEMONIC_API_URL", "http://localhost:8010"),
        "namespace": os.environ.get("MNEMONIC_NAMESPACE", "hermes:boss:hnoe:*"),
    }

    config_path = get_hermes_home() / "mnemonic.json"
    if config_path.exists():
        try:
            file_cfg = json.loads(config_path.read_text(encoding="utf-8"))
            config.update({k: v for k, v in file_cfg.items()
                           if v is not None and v != ""})
        except Exception:
            pass

    return config


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

SEARCH_SCHEMA = {
    "name": "mnemonic_search",
    "description": (
        "Search memories by keyword or semantic meaning. "
        "Returns relevant facts ranked by relevance. "
        "Use mode='keyword' for exact term matching, mode='vector' for semantic search."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "mode": {
                "type": "string",
                "description": "Search mode: 'keyword' (default) or 'vector'",
                "enum": ["keyword", "vector"],
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default: 5, max: 20).",
            },
        },
        "required": ["query"],
    },
}

EXTRACT_SCHEMA = {
    "name": "mnemonic_extract",
    "description": (
        "Extract and store facts from text. "
        "Automatically deduplicates and merges with existing memories."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to extract facts from."},
        },
        "required": ["text"],
    },
}


# ---------------------------------------------------------------------------
# MemoryProvider implementation
# ---------------------------------------------------------------------------

class MnemonicMemoryProvider(MemoryProvider):
    """Mnemonic memory with BM25 keyword search and vector search."""

    def __init__(self):
        self._config = None
        self._api_url = "http://localhost:8010"
        self._namespace = "hermes:boss:hnoe:*"
        self._session_id = "default"  # Default session_id
        self._prefetch_result = ""
        self._prefetch_lock = threading.Lock()
        # Circuit breaker state
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0

    @property
    def name(self) -> str:
        return "mnemonic"

    def is_available(self) -> bool:
        """Check if Mnemonic API is reachable."""
        cfg = _load_config()
        if not cfg.get("api_url"):
            return False
        
        # Quick health check
        try:
            r = httpx.get(f"{cfg['api_url']}/health", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def save_config(self, values, hermes_home):
        """Write config to $HERMES_HOME/mnemonic.json."""
        import json
        from pathlib import Path
        config_path = Path(hermes_home) / "mnemonic.json"
        config_path.write_text(json.dumps(values, indent=2), encoding="utf-8")

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize for a session."""
        self._config = _load_config()
        self._api_url = self._config.get("api_url", "http://localhost:8010")
        self._namespace = self._config.get("namespace", "hermes:boss:hnoe:*")
        self._session_id = session_id  # Store session_id for write operations
        logger.info(f"Mnemonic initialized: api_url={self._api_url}, namespace={self._namespace}, session_id={session_id}")

    def system_prompt_block(self) -> str:
        """Return text to include in the system prompt."""
        return "Mnemonic memory system is active. Use mnemonic_search to recall relevant context."

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context for the upcoming turn."""
        if self._is_breaker_open():
            logger.warning("Mnemonic circuit breaker open, skipping prefetch")
            return ""

        try:
            r = httpx.post(
                f"{self._api_url}/memories/search",
                headers={"X-Namespace": self._namespace},
                json={"query": query, "mode": "keyword", "limit": 3},
                timeout=5.0,
            )

            if r.status_code == 200:
                data = r.json()
                if data:
                    self._reset_breaker()
                    context = "相关历史记忆：\n"
                    for item in data:
                        # API returns list of {memory: {content: ...}}
                        content = item.get("memory", {}).get("content", "")
                        context += f"- {content}\n"
                    return context
            else:
                self._record_failure()
                logger.warning(f"Mnemonic search failed: {r.status_code}")
        except Exception as e:
            self._record_failure()
            logger.error(f"Mnemonic search error: {e}")

        return ""

    def sync_turn(self, user_message: str, assistant_message: str, session_id: str = None) -> None:
        """Sync turn to memory (async write).
        
        Args:
            user_message: User's message content
            assistant_message: Assistant's response (not used in extraction)
            session_id: Optional session ID override
        """
        # Only extract from user message, not assistant response
        if not user_message or self._is_breaker_open():
            return

        try:
            # Use session_id from parameter or instance
            effective_session = session_id or self._session_id or "default"
            # Replace wildcard with session_id for write operations
            write_ns = self._namespace.replace("*", effective_session)
            r = httpx.post(
                f"{self._api_url}/memories/extract",
                headers={"X-Namespace": write_ns},
                json={"conversation": user_message},
                timeout=10.0,
            )

            if r.status_code == 200:
                self._reset_breaker()
                logger.debug("Mnemonic extract success")
            else:
                self._record_failure()
                logger.warning(f"Mnemonic extract failed: {r.status_code}")
        except Exception as e:
            self._record_failure()
            logger.error(f"Mnemonic extract error: {e}")

    def get_tool_schemas(self) -> List[Dict]:
        """Return tool schemas to expose to the model."""
        return [SEARCH_SCHEMA, EXTRACT_SCHEMA]

    def handle_tool_call(self, name: str, arguments: Dict) -> str:
        """Handle a tool call from the model."""
        if name == "mnemonic_search":
            return self._handle_search(arguments)
        elif name == "mnemonic_extract":
            return self._handle_extract(arguments)
        else:
            return tool_error(f"Unknown tool: {name}")

    def _handle_search(self, args: Dict) -> str:
        """Handle mnemonic_search tool call."""
        query = args.get("query", "")
        mode = args.get("mode", "keyword")
        limit = min(args.get("limit", 5), 20)

        if not query:
            return tool_error("Query is required")

        if self._is_breaker_open():
            return "Mnemonic is temporarily unavailable (circuit breaker open)."

        try:
            r = httpx.post(
                f"{self._api_url}/memories/search",
                headers={"X-Namespace": self._namespace},
                json={"query": query, "mode": mode, "limit": limit},
                timeout=10.0,
            )

            if r.status_code == 200:
                self._reset_breaker()
                data = r.json()
                if not data:
                    return "No relevant memories found."
                
                result = f"Found {len(data)} relevant memories:\n\n"
                for i, item in enumerate(data, 1):
                    content = item.get("memory", {}).get("content", "")
                    result += f"{i}. {content}\n\n"
                return result
            else:
                self._record_failure()
                return tool_error(f"Search failed: {r.status_code}")
        except Exception as e:
            self._record_failure()
            return tool_error(f"Search error: {e}")

    def _handle_extract(self, args: Dict) -> str:
        """Handle mnemonic_extract tool call."""
        text = args.get("text", "")

        if not text:
            return tool_error("Text is required")

        if self._is_breaker_open():
            return "Mnemonic is temporarily unavailable (circuit breaker open)."

        try:
            # Replace wildcard with session_id for write operations
            write_ns = self._namespace.replace("*", self._session_id or "default")
            r = httpx.post(
                f"{self._api_url}/memories/extract",
                headers={"X-Namespace": write_ns},
                json={"conversation": text},  # API expects "conversation" field
                timeout=15.0,
            )

            if r.status_code in (200, 201):
                self._reset_breaker()
                data = r.json()
                if isinstance(data, list):
                    return f"Extracted {len(data)} memories."
                action = data.get("action", "NONE")
                if action == "ADD":
                    return "New memory added."
                elif action == "UPDATE":
                    return "Memory updated."
                elif action == "DELETE":
                    return "Memory deleted."
                else:
                    return "No changes (duplicate or irrelevant)."
            else:
                self._record_failure()
                return tool_error(f"Extract failed: {r.status_code}")
        except Exception as e:
            self._record_failure()
            return tool_error(f"Extract error: {e}")

    def shutdown(self) -> None:
        """Clean shutdown."""
        logger.info("Mnemonic shutdown")

    # -- Circuit breaker ------------------------------------------------------

    def _is_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        return time.time() < self._breaker_open_until

    def _record_failure(self) -> None:
        """Record a failure and potentially open the breaker."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= _BREAKER_THRESHOLD:
            self._breaker_open_until = time.time() + _BREAKER_COOLDOWN_SECS
            logger.error(
                f"Mnemonic circuit breaker opened for {_BREAKER_COOLDOWN_SECS}s "
                f"after {self._consecutive_failures} consecutive failures"
            )

    def _reset_breaker(self) -> None:
        """Reset circuit breaker on success."""
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0
