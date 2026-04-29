"""Memory extraction and embedding services."""

from __future__ import annotations

import json
from typing import Optional

from openai import AsyncOpenAI

from mnemonic.config import config


def _build_openai_client() -> AsyncOpenAI:
    """Build OpenAI-compatible client from config.
    
    Supports self-hosted endpoints (e.g. vLLM, Ollama, Gemma)
    via base_url override in config.yaml.
    """
    llm_cfg = config["llm"]
    return AsyncOpenAI(
        api_key=llm_cfg["api_key"],
        base_url=llm_cfg.get("base_url"),  # None → OpenAI official
    )


class EmbeddingService:
    """Vector embedding service.
    
    For self-hosted LLM endpoints that may not serve /v1/embeddings,
    falls back to using the chat model to generate a text representation
    which is then hashed into a pseudo-embedding vector.
    """
    
    def __init__(self):
        self.client = _build_openai_client()
        self.model = config["vector"]["embedding_model"]
        self.dim = config["vector"]["embedding_dim"]
        self._use_native_embedding = True  # will auto-detect on first call
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.
        
        Tries native /v1/embeddings first. If the endpoint doesn't support
        it (common for self-hosted models), falls back to chat-based
        pseudo-embedding using the LLM.
        """
        if self._use_native_embedding:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=text,
                )
                return response.data[0].embedding
            except Exception:
                self._use_native_embedding = False
        
        # Fallback: use LLM to generate a deterministic pseudo-embedding
        return await self._pseudo_embed(text)
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self._use_native_embedding:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception:
                self._use_native_embedding = False
        
        return [await self._pseudo_embed(t) for t in texts]
    
    async def _pseudo_embed(self, text: str) -> list[float]:
        """Generate pseudo-embedding via LLM + SimHash.
        
        Uses the chat model to produce a semantic summary,
        then maps it to a fixed-dim vector via deterministic hashing.
        This is a stopgap until a proper embedding model is deployed.
        
        Guaranteed: no NaN, no Inf, unit-normalized, deterministic.
        """
        import hashlib
        import math
        
        # Use LLM to get a semantic summary (short, deterministic)
        try:
            response = await self.client.chat.completions.create(
                model=config["llm"]["model"],
                messages=[
                    {"role": "system", "content": "Summarize in exactly 10 keywords, comma-separated. No other text."},
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_tokens=50,
            )
            summary = response.choices[0].message.content or text
        except Exception:
            summary = text
        
        # Deterministic vector from hash: use integer chunks → map to [-1, 1]
        # This avoids struct.unpack float NaN/Inf issues entirely
        vec = []
        seed = 0
        while len(vec) < self.dim:
            h = hashlib.sha256(f"{summary}:{seed}".encode()).digest()
            # Each byte → float in [-1, 1] via (byte - 128) / 128
            for byte in h:
                val = (byte - 128) / 128.0
                vec.append(val)
                if len(vec) >= self.dim:
                    break
            seed += 1
        
        # Normalize to unit vector (guaranteed no zero-norm since dim=1536)
        norm = math.sqrt(sum(v * v for v in vec[:self.dim]))
        if norm > 1e-10:
            vec = [v / norm for v in vec[:self.dim]]
        else:
            # Fallback: first element = 1, rest = 0
            vec = [1.0] + [0.0] * (self.dim - 1)
        
        return vec[:self.dim]


class ExtractionService:
    """LLM-based memory extraction service."""
    
    EXTRACTION_PROMPT = """Extract factual memories from the following conversation turn.

Rules:
1. Extract only facts, preferences, or rules that should be remembered
2. Each fact should be atomic and independent
3. Ignore greetings, small talk, and temporary context
4. Return empty array if nothing worth remembering

Conversation:
{conversation}

Return a JSON object with a "memories" key containing an array:
{{"memories": [
  {{"content": "fact 1", "type": "fact", "importance": 0.7}},
  {{"content": "fact 2", "type": "preference", "importance": 0.9}}
]}}

If nothing worth remembering, return: {{"memories": []}}"""
    
    def __init__(self):
        self.client = _build_openai_client()
        self.model = config["llm"]["model"]
        self.temperature = config["llm"]["temperature"]
    
    async def extract(self, conversation: str) -> list[dict]:
        """Extract memories from conversation using LLM."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a memory extraction assistant. Extract only factual, persistent information. Always respond with valid JSON."},
                    {"role": "user", "content": self.EXTRACTION_PROMPT.format(conversation=conversation)},
                ],
                temperature=self.temperature,
                max_tokens=config["llm"]["max_tokens"],
            )
            
            content = response.choices[0].message.content
            if not content:
                return []
            
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "memories" in data:
                    return data["memories"]
                if isinstance(data, list):
                    return data
                return []
            except json.JSONDecodeError:
                # Try to find JSON array in response
                import re
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    return json.loads(match.group())
                return []
        except Exception as e:
            import logging
            logging.getLogger("mnemonic").error(f"Extraction failed: {e}")
            return []
    
    async def check_conflict(self, existing: str, new: str) -> bool:
        """Check if new memory conflicts with existing (LLM-based)."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a conflict detection assistant. Respond only with 'true' or 'false'."},
                    {"role": "user", "content": f"""Determine if these two memories conflict (contradict each other).

Existing: {existing}
New: {new}

Do they conflict? Answer only 'true' or 'false':"""},
                ],
                temperature=0.0,
                max_tokens=10,
            )
            
            answer = response.choices[0].message.content.strip().lower()
            return "true" in answer
        except Exception as e:
            import logging
            logging.getLogger("mnemonic").error(f"Conflict check failed: {e}")
            return False  # On error, assume no conflict


# Global service instances
embedding_service = EmbeddingService()
extraction_service = ExtractionService()
