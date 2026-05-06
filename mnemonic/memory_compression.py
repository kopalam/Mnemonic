"""Memory Compression Algorithm.

Compresses multiple related memories into concise summaries.
Reduces storage and improves retrieval efficiency.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CompressionResult:
    """Result of memory compression."""
    compressed_memory: Dict
    source_memory_ids: List[str]
    compression_ratio: float
    compression_type: str


def compress_memories(
    memories: List[Dict],
    min_importance: float = 0.3,
) -> Optional[CompressionResult]:
    """
    Compress multiple memories into one summary.

    Args:
        memories: List of memories to compress
        min_importance: Minimum average importance to keep

    Returns:
        CompressionResult or None if not compressible
    """
    if len(memories) < 2:
        return None

    # Check if memories are related
    if not _are_memories_related(memories):
        return None

    # Calculate average importance
    avg_importance = sum(m.get("importance", 0.5) for m in memories) / len(memories)

    if avg_importance < min_importance:
        return None

    # Determine compression type
    compression_type = _determine_compression_type(memories)

    # Compress based on type
    if compression_type == "temporal_sequence":
        compressed = _compress_temporal_sequence(memories)
    elif compression_type == "entity_centric":
        compressed = _compress_entity_centric(memories)
    elif compression_type == "topic_cluster":
        compressed = _compress_topic_cluster(memories)
    else:
        compressed = _compress_generic(memories)

    # Calculate compression ratio
    original_length = sum(len(m.get("content", "")) for m in memories)
    compressed_length = len(compressed.get("content", ""))
    compression_ratio = 1 - (compressed_length / original_length) if original_length > 0 else 0

    return CompressionResult(
        compressed_memory=compressed,
        source_memory_ids=[m.get("id") for m in memories],
        compression_ratio=compression_ratio,
        compression_type=compression_type,
    )


def _are_memories_related(memories: List[Dict]) -> bool:
    """
    Check if memories are related enough to compress.

    Heuristic:
    - Share common entities
    - Share common keywords
    - Temporal proximity
    """
    if len(memories) < 2:
        return False

    # Extract entities from all memories
    all_entities = []
    for mem in memories:
        content = mem.get("content", "")
        entities = set(re.findall(r'\b[A-Z][a-z]+\b', content))
        all_entities.append(entities)

    # Check for shared entities
    common_entities = all_entities[0]
    for entities in all_entities[1:]:
        common_entities = common_entities & entities

    # If at least one common entity, they're related
    if len(common_entities) > 0:
        return True

    # Check for keyword overlap
    all_keywords = []
    for mem in memories:
        content = mem.get("content", "").lower()
        keywords = set(content.split())
        all_keywords.append(keywords)

    common_keywords = all_keywords[0]
    for keywords in all_keywords[1:]:
        common_keywords = common_keywords & keywords

    # Filter short words
    common_keywords = {k for k in common_keywords if len(k) > 3}

    # Require at least 2 common keywords for unrelated detection
    # This prevents false positives from generic words like "fact", "random"
    if len(common_keywords) >= 3:
        return True

    return False


def _determine_compression_type(memories: List[Dict]) -> str:
    """
    Determine the best compression strategy.

    Types:
    - temporal_sequence: Events in sequence
    - entity_centric: Multiple facts about same entity
    - topic_cluster: Related topics
    - generic: Default compression
    """
    # Check for entity-centric first (more specific)
    entities = []
    for mem in memories:
        content = mem.get("content", "")
        entity_list = re.findall(r'\b[A-Z][a-z]+\b', content)
        entities.extend(entity_list)

    if entities and len(set(entities)) <= 2:
        return "entity_centric"

    # Check for temporal sequence
    has_temporal = any(_has_temporal_reference(m.get("content", "")) for m in memories)
    if has_temporal:
        return "temporal_sequence"

    # Default to topic cluster
    return "topic_cluster"


def _has_temporal_reference(text: str) -> bool:
    """Check if text has temporal references."""
    temporal_patterns = [
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}:\d{2}',
        r'(yesterday|tomorrow|today)',
        r'(last|next)\s+(week|month|year)',
        r'\d+\s+(hour|day|week|month|year)s?',
    ]

    for pattern in temporal_patterns:
        if re.search(pattern, text, re.I):
            return True

    return False


def _compress_temporal_sequence(memories: List[Dict]) -> Dict:
    """
    Compress temporal sequence of events.

    Strategy: Summarize as "X happened, then Y, then Z"
    """
    # Sort by timestamp if available
    sorted_memories = sorted(
        memories,
        key=lambda m: m.get("created_at", datetime.max.isoformat())
    )

    # Extract key events
    events = []
    for mem in sorted_memories:
        content = mem.get("content", "")
        # Extract first sentence as event
        first_sentence = content.split(".")[0].strip()
        events.append(first_sentence)

    # Create summary
    if len(events) <= 3:
        summary = " → ".join(events)
    else:
        summary = f"{events[0]} → ... → {events[-1]} ({len(events)} events total)"

    # Create compressed memory
    compressed = {
        "content": summary,
        "type": "event",
        "importance": max(m.get("importance", 0.5) for m in memories),
        "compressed_from": [m.get("id") for m in memories],
        "compression_type": "temporal_sequence",
    }

    return compressed


def _compress_entity_centric(memories: List[Dict]) -> Dict:
    """
    Compress multiple facts about same entity.

    Strategy: "Entity: fact1, fact2, fact3"
    """
    # Extract common entity
    all_entities = []
    for mem in memories:
        content = mem.get("content", "")
        entities = re.findall(r'\b[A-Z][a-z]+\b', content)
        all_entities.extend(entities)

    # Most common entity
    from collections import Counter
    entity_counts = Counter(all_entities)
    main_entity = entity_counts.most_common(1)[0][0] if entity_counts else "Entity"

    # Extract facts
    facts = []
    for mem in memories:
        content = mem.get("content", "")
        # Remove entity name to get fact
        fact = content.replace(main_entity, "").strip()
        # Clean up
        fact = re.sub(r'^\s*(is|are|was|were|has|have|had)\s+', "", fact)
        if fact:
            facts.append(fact)

    # Create summary
    summary = f"{main_entity}: {', '.join(facts[:5])}"
    if len(facts) > 5:
        summary += f" ... ({len(facts)} facts total)"

    # Create compressed memory
    compressed = {
        "content": summary,
        "type": "fact",
        "importance": max(m.get("importance", 0.5) for m in memories),
        "compressed_from": [m.get("id") for m in memories],
        "compression_type": "entity_centric",
    }

    return compressed


def _compress_topic_cluster(memories: List[Dict]) -> Dict:
    """
    Compress topic cluster.

    Strategy: Extract key points and summarize
    """
    # Extract keywords
    all_keywords = []
    for mem in memories:
        content = mem.get("content", "").lower()
        keywords = [w for w in content.split() if len(w) > 3]
        all_keywords.extend(keywords)

    # Top keywords
    from collections import Counter
    keyword_counts = Counter(all_keywords)
    top_keywords = [k for k, _ in keyword_counts.most_common(5)]

    # Create summary
    summary = f"Related memories about: {', '.join(top_keywords)}"
    summary += f" ({len(memories)} memories compressed)"

    # Create compressed memory
    compressed = {
        "content": summary,
        "type": "fact",
        "importance": sum(m.get("importance", 0.5) for m in memories) / len(memories),
        "compressed_from": [m.get("id") for m in memories],
        "compression_type": "topic_cluster",
    }

    return compressed


def _compress_generic(memories: List[Dict]) -> Dict:
    """
    Generic compression strategy.

    Strategy: Concatenate and truncate
    """
    # Concatenate all content
    all_content = " | ".join(m.get("content", "") for m in memories)

    # Truncate if too long
    max_length = 500
    if len(all_content) > max_length:
        all_content = all_content[:max_length] + "..."

    # Create compressed memory
    compressed = {
        "content": all_content,
        "type": "fact",
        "importance": sum(m.get("importance", 0.5) for m in memories) / len(memories),
        "compressed_from": [m.get("id") for m in memories],
        "compression_type": "generic",
    }

    return compressed


def should_compress(memories: List[Dict], threshold: int = 5) -> bool:
    """
    Determine if memories should be compressed.

    Args:
        memories: List of memories
        threshold: Minimum number of memories to consider compression

    Returns:
        True if compression is recommended
    """
    if len(memories) < threshold:
        return False

    # Check if related
    if not _are_memories_related(memories):
        return False

    # Check average importance
    avg_importance = sum(m.get("importance", 0.5) for m in memories) / len(memories)
    if avg_importance < 0.3:
        return False

    return True