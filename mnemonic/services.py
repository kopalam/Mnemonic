"""Memory extraction and embedding services.

Based on mem0 architecture:
- ADDITIVE_EXTRACTION_PROMPT: ADD-only extraction with linking
- UPDATE_MEMORY_PROMPT: ADD/UPDATE/DELETE/NONE decision
- Weighted RRF for hybrid retrieval
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import jieba
from openai import AsyncOpenAI

from mnemonic.config import config

logger = logging.getLogger("mnemonic")


def _build_openai_client(base_url: str, api_key: str, timeout: int = 120) -> AsyncOpenAI:
    """Build OpenAI-compatible client with explicit params."""
    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )


class LLMClient:
    """LLM client with automatic failover from primary to fallback."""
    
    def __init__(self):
        llm_cfg = config["llm"]
        failover_cfg = llm_cfg.get("failover", {})
        
        # Primary client
        primary = llm_cfg["primary"]
        self.primary_client = _build_openai_client(
            base_url=primary["base_url"],
            api_key=primary["api_key"],
            timeout=primary.get("timeout", 120),
        )
        self.primary_model = primary["model"]
        
        # Fallback client
        fallback = llm_cfg["fallback"]
        self.fallback_client = _build_openai_client(
            base_url=fallback["base_url"],
            api_key=fallback["api_key"],
            timeout=fallback.get("timeout", 60),
        )
        self.fallback_model = fallback["model"]
        
        # Failover config
        self.max_retries = failover_cfg.get("max_retries", 2)
        self.retry_delay = failover_cfg.get("retry_delay", 2)
        self.error_codes = failover_cfg.get("error_codes", [500, 502, 503, 504])
        self.timeout_trigger = failover_cfg.get("timeout_trigger", True)
        
        # State tracking
        self._using_fallback = False
        self._primary_fail_count = 0
        self._fallback_fail_count = 0
        self._last_primary_check = 0.0
        self._primary_check_interval = 300  # 5 min
    
    @property
    def active_model(self) -> str:
        return self.fallback_model if self._using_fallback else self.primary_model
    
    async def chat_completion(self, messages: list[dict], temperature: float = 0.1,
                              max_tokens: int = 1000) -> str:
        """Send chat completion with automatic failover."""
        if self._using_fallback:
            if time.monotonic() - self._last_primary_check > self._primary_check_interval:
                try:
                    resp = await self.primary_client.chat.completions.create(
                        model=self.primary_model,
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=5,
                    )
                    self._using_fallback = False
                    self._primary_fail_count = 0
                    logger.info(f"Primary LLM ({self.primary_model}) recovered")
                except Exception:
                    self._last_primary_check = time.monotonic()
        
        if not self._using_fallback:
            last_err = None
            for attempt in range(1 + self.max_retries):
                try:
                    response = await self.primary_client.chat.completions.create(
                        model=self.primary_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    self._primary_fail_count = 0
                    return response.choices[0].message.content or ""
                except Exception as e:
                    last_err = e
                    self._primary_fail_count += 1
                    should_failover = self._should_failover(e)
                    logger.warning(f"Primary LLM attempt {attempt+1} failed: {e}")
                    if should_failover or attempt == self.max_retries:
                        break
                    await asyncio.sleep(self.retry_delay)
            
            logger.warning(f"Switching to fallback. Error: {last_err}")
            self._using_fallback = True
            self._last_primary_check = time.monotonic()
        
        try:
            response = await self.fallback_client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._fallback_fail_count = 0
            return response.choices[0].message.content or ""
        except Exception as e:
            self._fallback_fail_count += 1
            logger.error(f"Fallback LLM also failed: {e}")
            raise
    
    def _should_failover(self, error: Exception) -> bool:
        err_str = str(error)
        for code in self.error_codes:
            if str(code) in err_str:
                return True
        if self.timeout_trigger and ("timeout" in err_str.lower() or "timed out" in err_str.lower()):
            return True
        if "connection" in err_str.lower() or "connect" in err_str.lower():
            return True
        return False


class EmbeddingService:
    """Vector embedding service via SiliconFlow API."""
    
    def __init__(self):
        emb_cfg = config["vector"]["embedding"]
        self.client = AsyncOpenAI(
            api_key=emb_cfg["api_key"],
            base_url=emb_cfg["base_url"],
        )
        self.model = emb_cfg["model"]
        self.dim = emb_cfg["dim"]
        self._fallback = False
    
    async def embed(self, text: str) -> list[float]:
        if self._fallback:
            return await self._pseudo_embed(text)
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            vec = response.data[0].embedding
            if len(vec) != self.dim:
                logger.warning(f"Embedding dim mismatch: got {len(vec)}, expected {self.dim}")
            return vec
        except Exception as e:
            logger.error(f"Embedding API failed: {e}")
            self._fallback = True
            return await self._pseudo_embed(text)
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._fallback:
            return [await self._pseudo_embed(t) for t in texts]
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            self._fallback = True
            return [await self._pseudo_embed(t) for t in texts]
    
    async def _pseudo_embed(self, text: str) -> list[float]:
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


# ─── mem0-inspired Prompts ─────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a Personal Information Organizer, specialized in accurately storing facts, user memories, and preferences.

Your primary role is to extract relevant pieces of information from conversations and organize them into distinct, manageable facts.

Types of Information to Remember:
1. Personal Preferences: likes, dislikes, specific preferences (food, products, activities)
2. Important Personal Details: names, relationships, important dates
3. Plans and Intentions: upcoming events, trips, goals
4. Activity and Service Preferences: dining, travel, hobbies
5. Health and Wellness: dietary restrictions, fitness routines
6. Professional Details: job titles, work habits, career goals
7. Miscellaneous: favorite books, movies, brands

Memory Quality Standards:
- Contextually Rich: Capture the full picture, not just atomic facts
- Clean Factual Statements: Remove filler words, keep emotional states and motivations
- Self-Contained: Replace pronouns with specific names or "User"
- Concise but Complete: 15-80 words per memory
- Temporally Grounded: Preserve exact dates and durations
- Numerically Precise: Keep exact quantities

CRITICAL LANGUAGE RULE: You MUST output memories in the EXACT SAME LANGUAGE as the input. If the input is in Chinese, the output MUST be in Chinese. If the input is in Japanese, output in Japanese. NEVER translate to English. This is essential for search retrieval accuracy."""

EXTRACTION_USER_PROMPT = """Extract factual memories from the following conversation.

Today's date: {date}

Conversation:
{conversation}

Return a JSON object:
{{"memories": [
  {{"content": "fact 1", "type": "fact", "importance": 0.7}},
  {{"content": "fact 2", "type": "preference", "importance": 0.9}}
]}}

If nothing worth remembering, return: {{"memories": []}}"""

# mem0-style UPDATE prompt (ADD/UPDATE/DELETE/NONE decision)
UPDATE_MEMORY_PROMPT = """You are a smart memory manager which controls the memory of a system.
You can perform four operations: (1) add into the memory, (2) update the memory, (3) delete from the memory, and (4) no change.

Based on the above four operations, the memory will change.

Compare newly retrieved facts with the existing memory. For each new fact, decide whether to:
- ADD: Add it to the memory as a new element
- UPDATE: Update an existing memory element
- DELETE: Delete an existing memory element
- NONE: Make no change (if the fact is already present or irrelevant)

Guidelines:

1. **Add**: If the retrieved facts contain new information not present in the memory.
   Example:
   - Old Memory: [{{"id": "0", "text": "User is a software engineer"}}]
   - Retrieved facts: ["Name is John"]
   - New Memory: {{
       "memory": [
         {{"id": "0", "text": "User is a software engineer", "event": "NONE"}},
         {{"id": "1", "text": "Name is John", "event": "ADD"}}
       ]
     }}

2. **Update**: If the retrieved facts contain information that complements or corrects existing memory.
   Keep the same ID when updating.
   Example:
   - Old Memory: [{{"id": "0", "text": "Likes cheese pizza"}}]
   - Retrieved facts: ["Loves chicken pizza"]
   - New Memory: {{
       "memory": [
         {{"id": "0", "text": "Loves cheese and chicken pizza", "event": "UPDATE", "old_memory": "Likes cheese pizza"}}
       ]
     }}

3. **Delete**: If the retrieved facts contradict existing memory.
   Example:
   - Old Memory: [{{"id": "0", "text": "Loves cheese pizza"}}]
   - Retrieved facts: ["Dislikes cheese pizza"]
   - New Memory: {{
       "memory": [
         {{"id": "0", "text": "Loves cheese pizza", "event": "DELETE"}}
       ]
     }}

4. **No Change**: If the retrieved facts are already present or irrelevant.
   Example:
   - Old Memory: [{{"id": "0", "text": "Name is John"}}]
   - Retrieved facts: ["Name is John"]
   - New Memory: {{
       "memory": [
         {{"id": "0", "text": "Name is John", "event": "NONE"}}
       ]
     }}

CRITICAL LANGUAGE RULE: You MUST output memories in the EXACT SAME LANGUAGE as the input. If the input is in Chinese, the output MUST be in Chinese. If the input is in Japanese, output in Japanese. NEVER translate to English. This is essential for search retrieval accuracy."""


class ExtractionService:
    """LLM-based memory extraction service (mem0-style)."""
    
    def __init__(self):
        self.llm = LLMClient()
        self.temperature = config["llm"]["temperature"]
        self.max_tokens = config["llm"]["max_tokens"]
    
    async def extract(self, conversation: str) -> list[dict]:
        """Extract memories from conversation using mem0-style prompt."""
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            content = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": EXTRACTION_USER_PROMPT.format(
                        date=today,
                        conversation=conversation
                    )},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            if not content:
                return []
            
            # Strip markdown code fences
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
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    return json.loads(match.group())
                return []
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return []
    
    async def decide_memory_action(
        self,
        existing_memories: list[dict],
        new_facts: list[str]
    ) -> list[dict]:
        """Decide ADD/UPDATE/DELETE/NONE for each new fact (mem0-style).
        
        Args:
            existing_memories: List of {"id": str, "text": str}
            new_facts: List of new fact strings
        
        Returns:
            List of {"id": str, "text": str, "event": "ADD"|"UPDATE"|"DELETE"|"NONE", "old_memory": str?}
        """
        if not new_facts:
            return []
        
        if not existing_memories:
            # All new facts are ADD
            return [
                {"id": str(i), "text": fact, "event": "ADD"}
                for i, fact in enumerate(new_facts)
            ]
        
        try:
            old_memory_json = json.dumps(existing_memories, ensure_ascii=False, indent=2)
            new_facts_json = json.dumps(new_facts, ensure_ascii=False, indent=2)
            
            prompt = f"""{UPDATE_MEMORY_PROMPT}

Old Memory:
{old_memory_json}

Retrieved facts:
{new_facts_json}

Return the New Memory JSON:"""
            
            content = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a memory manager. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=2000,
            )
            
            if not content:
                # Fallback: treat all as ADD
                return [
                    {"id": str(len(existing_memories) + i), "text": fact, "event": "ADD"}
                    for i, fact in enumerate(new_facts)
                ]
            
            # Strip markdown
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "memory" in data:
                    return data["memory"]
                return []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse memory action response: {content[:200]}")
                return [
                    {"id": str(len(existing_memories) + i), "text": fact, "event": "ADD"}
                    for i, fact in enumerate(new_facts)
                ]
        except Exception as e:
            logger.error(f"Memory action decision failed: {e}")
            return [
                {"id": str(len(existing_memories) + i), "text": fact, "event": "ADD"}
                for i, fact in enumerate(new_facts)
            ]
    
    async def check_conflict(self, existing: str, new: str) -> bool:
        """Check if new memory conflicts with existing."""
        try:
            answer = await self.llm.chat_completion(
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
            
            return "true" in answer.strip().lower()
        except Exception as e:
            logger.error(f"Conflict check failed: {e}")
            return False


# Global service instances
embedding_service = EmbeddingService()
extraction_service = ExtractionService()


# ─── Entity Extraction & Boost ──────────────────────────────────────────

ENTITY_EXTRACTION_PROMPT = """You are an entity extraction specialist. Extract named entities from the given text.

For each entity, provide:
- name: the exact entity text
- type: one of [PERSON, PROJECT, TECHNOLOGY, PLATFORM, LOCATION, ORGANIZATION, PRODUCT, CONFIG, METRIC, TIME, CURRENCY, UNKNOWN]

Rules:
- Extract only concrete, specific entities (not generic words)
- Keep original language (Chinese stays Chinese, English stays English)
- Be conservative: only extract entities that would be useful for search boosting

Return JSON: {"entities": [{"name": "...", "type": "..."}]}
If no entities found, return: {"entities": []}"""


class EntityService:
    """Entity extraction and linking service (mem0-style)."""
    
    def __init__(self):
        self.llm = LLMClient()
    
    async def extract(self, text: str) -> list[dict]:
        """Extract entities from text using LLM."""
        try:
            content = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": ENTITY_EXTRACTION_PROMPT},
                    {"role": "user", "content": f"Extract entities from:\n\n{text}"},
                ],
                temperature=0.0,
                max_tokens=500,
            )
            
            if not content:
                return []
            
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            data = json.loads(content)
            if isinstance(data, dict) and "entities" in data:
                return data["entities"]
            return []
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    async def extract_simple(self, text: str) -> list[dict]:
        """Fast entity extraction using regex patterns (no LLM call).
        
        Fallback when LLM is unavailable. Catches common patterns:
        - English technical terms (CCXT, FastAPI, etc.)
        - Numbers with units (3-10x, 8010, 15分钟)
        - Chinese business concepts (趋势跟随, 杠杆, 止损)
        - Known project names from common patterns
        """
        entities = []
        seen = set()
        
        # English technical terms (2+ letters, not all lowercase)
        # Note: No \b word boundary - Chinese chars don't have boundaries with English
        for m in re.finditer(r'([A-Za-z][A-Za-z0-9]*(?:[-.][A-Za-z0-9]+)*)', text):
            name = m.group(1)
            if len(name) >= 2 and not name.islower() and name not in seen:
                seen.add(name)
                entities.append({"name": name, "type": "TECHNOLOGY"})
        
        # Numbers with units (e.g., 3-10x, 8010, 15分钟)
        for m in re.finditer(r'(\d+(?:-\d+)?(?:x|端口|分钟|小时|天|周|月|年|%|维|级|m|h))', text):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                entities.append({"name": name, "type": "METRIC"})
        
        # Chinese business concepts (2-4 chars common terms)
        chinese_concepts = [
            "趋势跟随", "杠杆", "止损", "止盈", "回测", "实盘", "模拟盘",
            "K线", "周期", "策略", "信号", "持仓", "仓位", "风控",
            "RPC", "MEV", "Meme", "Bot", "API", "LLM", "降级",
        ]
        for concept in chinese_concepts:
            if concept in text and concept not in seen:
                seen.add(concept)
                entities.append({"name": concept, "type": "CONCEPT"})
        
        # API keys / identifiers
        for m in re.finditer(r'([a-zA-Z0-9_-]{8,})', text):
            name = m.group(1)
            if name not in seen and not name.isalpha():
                seen.add(name)
                entities.append({"name": name, "type": "CONFIG"})
        
        return entities


entity_service = EntityService()


# ─── Jieba Chinese tokenizer ────────────────────────────────────────────

def tokenize_for_search(text: str) -> str:
    """Tokenize text with jieba for PostgreSQL tsvector/tsquery."""
    tokens = jieba.cut_for_search(text)
    cleaned = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if re.match(r'^[\u4e00-\u9fff]+$', t):
            if len(t) >= 2:
                cleaned.append(t)
        elif re.match(r'^[a-zA-Z0-9]+$', t):
            cleaned.append(t)
        elif re.match(r'^[\w.-]+$', t):
            cleaned.append(t)
    
    return ' '.join(cleaned)


def make_tsquery_str(text: str) -> str:
    """Build a tsquery-friendly string from query text."""
    tokens = tokenize_for_search(text).split()
    if not tokens:
        return ''
    return ' & '.join(tokens)
