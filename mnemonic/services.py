"""Memory extraction and embedding services."""

import json
from typing import Optional

from openai import AsyncOpenAI

from mnemonic.config import config


class EmbeddingService:
    """Vector embedding service using OpenAI."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config["llm"]["api_key"])
        self.model = config["vector"]["embedding_model"]
        self.dim = config["vector"]["embedding_dim"]
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]


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

Return JSON array of objects:
[
  {{"content": "fact 1", "type": "fact", "importance": 0.7}},
  {{"content": "fact 2", "type": "preference", "importance": 0.9}}
]

Only return the JSON array, no other text."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config["llm"]["api_key"])
        self.model = config["llm"]["model"]
        self.temperature = config["llm"]["temperature"]
    
    async def extract(self, conversation: str) -> list[dict]:
        """Extract memories from conversation using LLM."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a memory extraction assistant. Extract only factual, persistent information."},
                {"role": "user", "content": self.EXTRACTION_PROMPT.format(conversation=conversation)},
            ],
            temperature=self.temperature,
            max_tokens=config["llm"]["max_tokens"],
            response_format={"type": "json_object"},
        )
        
        content = response.choices[0].message.content
        if not content:
            return []
        
        try:
            data = json.loads(content)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
    
    async def check_conflict(self, existing: str, new: str) -> bool:
        """Check if new memory conflicts with existing (LLM-based)."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a conflict detection assistant."},
                {"role": "user", "content": f"""Determine if these two memories conflict (contradict each other).

Existing: {existing}
New: {new}

Return only "true" if they conflict, "false" otherwise."""},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        
        return response.choices[0].message.content.strip().lower() == "true"


# Global service instances
embedding_service = EmbeddingService()
extraction_service = ExtractionService()
