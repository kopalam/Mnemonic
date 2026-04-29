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
    """Vector embedding service via SiliconFlow API.
    
    Uses Qwen3-Embedding-8B (4096-dim) for semantic vectorization.
    Falls back to pseudo-embedding only on API failure.
    """
    
    def __init__(self):
        emb_cfg = config["vector"]["embedding"]
        self.client = AsyncOpenAI(
            api_key=emb_cfg["api_key"],
            base_url=emb_cfg["base_url"],
        )
        self.model = emb_cfg["model"]
        self.dim = emb_cfg["dim"]
        self._fallback = False  # set True if API permanently fails
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        if self._fallback:
            return await self._pseudo_embed(text)
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            vec = response.data[0].embedding
            if len(vec) != self.dim:
                import logging
                logging.getLogger("mnemonic").warning(
                    f"Embedding dim mismatch: got {len(vec)}, expected {self.dim}"
                )
            return vec
        except Exception as e:
            import logging
            logging.getLogger("mnemonic").error(f"Embedding API failed: {e}")
            self._fallback = True
            return await self._pseudo_embed(text)
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self._fallback:
            return [await self._pseudo_embed(t) for t in texts]
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            import logging
            logging.getLogger("mnemonic").error(f"Batch embedding failed: {e}")
            self._fallback = True
            return [await self._pseudo_embed(t) for t in texts]
    
    async def _pseudo_embed(self, text: str) -> list[float]:
        """Fallback: deterministic hash-based pseudo-embedding."""
        import hashlib
        import math
        
        vec = []
        seed = 0
        while len(vec) < self.dim:
            h = hashlib.sha256(f"{text}:{seed}".encode()).digest()
            for byte in h:
                vec.append((byte - 128) / 128.0)
                if len(vec) >= self.dim:
                    break
            seed += 1
        
        norm = math.sqrt(sum(v * v for v in vec[:self.dim]))
        if norm > 1e-10:
            vec = [v / norm for v in vec[:self.dim]]
        else:
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
