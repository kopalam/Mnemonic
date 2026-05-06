"""Conflict Detection and Merge Algorithm.

Based on Mem0g's conflict detection mechanism.
Detects and resolves conflicts between memories.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ConflictType(Enum):
    """Types of memory conflicts."""
    CONTRADICTION = "contradiction"  # Direct contradiction
    UPDATE = "update"  # Newer info updates older
    DUPLICATE = "duplicate"  # Same info
    COMPLEMENTARY = "complementary"  # Adds new info
    NONE = "none"  # No conflict


@dataclass
class Conflict:
    """Detected conflict between memories."""
    type: ConflictType
    memory_id_1: str
    memory_id_2: str
    reason: str
    resolution: Optional[str] = None


def detect_conflict(
    memory_1: Dict,
    memory_2: Dict,
) -> ConflictType:
    """
    Detect conflict type between two memories.

    Args:
        memory_1: First memory (older)
        memory_2: Second memory (newer)

    Returns:
        ConflictType
    """
    content_1 = memory_1.get("content", "").lower()
    content_2 = memory_2.get("content", "").lower()

    # Check for exact duplicate
    if content_1 == content_2:
        return ConflictType.DUPLICATE

    # Check for contradiction first (highest priority)
    if _is_contradiction(content_1, content_2):
        return ConflictType.CONTRADICTION

    # Check for update (same entity, different value)
    if _is_update(memory_1, memory_2):
        return ConflictType.UPDATE

    # Check for semantic similarity (simple heuristic)
    similarity = _calculate_similarity(content_1, content_2)

    if similarity > 0.85:
        return ConflictType.DUPLICATE
    elif similarity > 0.5:
        return ConflictType.COMPLEMENTARY

    return ConflictType.NONE


def resolve_conflict(
    conflict: Conflict,
    memory_1: Dict,
    memory_2: Dict,
) -> Dict:
    """
    Resolve conflict between two memories.

    Args:
        conflict: Detected conflict
        memory_1: First memory (older)
        memory_2: Second memory (newer)

    Returns:
        Resolved memory (or memory_2 if no merge needed)
    """
    if conflict.type == ConflictType.DUPLICATE:
        # Keep the newer one with combined access count
        resolved = memory_2.copy()
        resolved["access_count"] = (
            memory_1.get("access_count", 0) +
            memory_2.get("access_count", 0)
        )
        conflict.resolution = "kept_newer_duplicate"
        return resolved

    elif conflict.type == ConflictType.CONTRADICTION:
        # Keep newer, mark older as superseded
        resolved = memory_2.copy()
        resolved["supersedes"] = memory_1.get("id")
        conflict.resolution = "kept_newer_contradiction"
        return resolved

    elif conflict.type == ConflictType.UPDATE:
        # Merge information
        resolved = _merge_memories(memory_1, memory_2)
        conflict.resolution = "merged_update"
        return resolved

    elif conflict.type == ConflictType.COMPLEMENTARY:
        # Keep both, they add to each other
        conflict.resolution = "keep_both_complementary"
        return memory_2

    else:
        # No conflict, keep both
        conflict.resolution = "keep_both_no_conflict"
        return memory_2


def detect_all_conflicts(
    memories: List[Dict],
) -> List[Conflict]:
    """
    Detect all conflicts in a list of memories.

    Args:
        memories: List of memories

    Returns:
        List of detected conflicts
    """
    conflicts = []

    for i, mem_1 in enumerate(memories):
        for j, mem_2 in enumerate(memories[i + 1:], start=i + 1):
            conflict_type = detect_conflict(mem_1, mem_2)

            if conflict_type != ConflictType.NONE:
                conflict = Conflict(
                    type=conflict_type,
                    memory_id_1=mem_1.get("id", str(i)),
                    memory_id_2=mem_2.get("id", str(j)),
                    reason=_get_conflict_reason(conflict_type),
                )
                conflicts.append(conflict)

    return conflicts


def _calculate_similarity(text_1: str, text_2: str) -> float:
    """
    Calculate simple text similarity (Jaccard similarity).

    Args:
        text_1: First text
        text_2: Second text

    Returns:
        Similarity score (0-1)
    """
    words_1 = set(text_1.lower().split())
    words_2 = set(text_2.lower().split())

    if not words_1 or not words_2:
        return 0.0

    intersection = words_1 & words_2
    union = words_1 | words_2

    return len(intersection) / len(union)


def _is_contradiction(text_1: str, text_2: str) -> bool:
    """
    Check if two texts contradict each other.

    Heuristic: Look for negation patterns.
    """
    # Extract key statements
    # Pattern: "X is Y" vs "X is not Y"
    # Pattern: "X likes Y" vs "X dislikes Y"

    contradiction_pairs = [
        ("likes", "dislikes"),
        ("loves", "hates"),
        ("wants", "doesn't want"),
        ("is", "is not"),
        ("is", "isn't"),
        ("has", "doesn't have"),
        ("can", "cannot"),
        ("can", "can't"),
        ("will", "won't"),
        ("should", "shouldn't"),
        ("single", "married"),
        ("doesn't like", "likes"),
        ("doesn't love", "loves"),
    ]

    # Check for direct negation
    for pos, neg in contradiction_pairs:
        if pos in text_1 and neg in text_2:
            return True
        if neg in text_1 and pos in text_2:
            return True
    
    # Check for "doesn't ... anymore" pattern
    if "doesn't" in text_2 and "anymore" in text_2:
        # Extract the verb/noun being negated
        # e.g., "doesn't like pizza anymore" vs "likes pizza"
        words_1 = set(text_1.split())
        words_2 = set(text_2.split())
        common = words_1 & words_2
        # If they share significant words, it's a contradiction
        if len(common) >= 2:
            return True

    return False


def _is_update(memory_1: Dict, memory_2: Dict) -> bool:
    """
    Check if memory_2 is an update of memory_1.

    Heuristic: Same entity, different value.
    """
    content_1 = memory_1.get("content", "").lower()
    content_2 = memory_2.get("content", "").lower()

    # Extract entities (capitalized words)
    entities_1 = set(re.findall(r'\b[A-Z][a-z]+\b', memory_1.get("content", "")))
    entities_2 = set(re.findall(r'\b[A-Z][a-z]+\b', memory_2.get("content", "")))

    # If they share entities but have different content
    shared_entities = entities_1 & entities_2

    if shared_entities and content_1 != content_2:
        return True
    
    # Check for same attribute pattern
    # e.g., "lives in X" vs "lives in Y"
    attribute_patterns = [
        r'(lives in|works at|is (\d+) years old|age is (\d+))',
    ]
    
    for pattern in attribute_patterns:
        match_1 = re.search(pattern, content_1)
        match_2 = re.search(pattern, content_2)
        
        if match_1 and match_2:
            # Same attribute, different value
            return True
    
    # Check for number differences (age, etc.)
    numbers_1 = re.findall(r'\d+', content_1)
    numbers_2 = re.findall(r'\d+', content_2)
    
    if numbers_1 and numbers_2 and numbers_1 != numbers_2:
        # Different numbers might indicate update
        # Check if they share other keywords
        words_1 = set(content_1.split())
        words_2 = set(content_2.split())
        common = words_1 & words_2
        if len(common) >= 3:  # Enough overlap to be same topic
            return True

    return False


def _merge_memories(memory_1: Dict, memory_2: Dict) -> Dict:
    """
    Merge two memories into one.

    Strategy:
    - Combine content
    - Keep newer timestamp
    - Sum access counts
    - Keep higher importance
    """
    merged = memory_2.copy()

    # Combine content (simple concatenation with separator)
    content_1 = memory_1.get("content", "")
    content_2 = memory_2.get("content", "")

    if content_1 and content_2 and content_1 != content_2:
        merged["content"] = f"{content_2} (previously: {content_1})"

    # Sum access counts
    merged["access_count"] = (
        memory_1.get("access_count", 0) +
        memory_2.get("access_count", 0)
    )

    # Keep higher importance
    merged["importance"] = max(
        memory_1.get("importance", 0.5),
        memory_2.get("importance", 0.5),
    )

    # Track merge history
    merged["merged_from"] = [memory_1.get("id")]

    return merged


def _get_conflict_reason(conflict_type: ConflictType) -> str:
    """Get human-readable reason for conflict type."""
    reasons = {
        ConflictType.CONTRADICTION: "Memories directly contradict each other",
        ConflictType.UPDATE: "Newer memory updates older memory",
        ConflictType.DUPLICATE: "Memories are duplicates",
        ConflictType.COMPLEMENTARY: "Memories complement each other",
        ConflictType.NONE: "No conflict detected",
    }
    return reasons.get(conflict_type, "Unknown conflict type")