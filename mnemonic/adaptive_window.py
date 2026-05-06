"""Adaptive Extraction Window Algorithm.

Based on IGMiRAG's adaptive cost control.
Dynamically adjusts extraction window size based on conversation complexity.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ExtractionWindow:
    """Extraction window configuration."""
    m: int  # Context window size (previous messages)
    s: int  # Similar memories to retrieve
    mode: str  # fast/standard/deep


# Window size presets
WINDOW_PRESETS = {
    "fast": ExtractionWindow(m=5, s=5, mode="fast"),
    "standard": ExtractionWindow(m=10, s=10, mode="standard"),
    "deep": ExtractionWindow(m=20, s=15, mode="deep"),
}


def determine_extraction_window(
    conversation: List[Dict[str, str]],
) -> ExtractionWindow:
    """
    Determine extraction window size based on conversation complexity.

    Args:
        conversation: List of conversation messages

    Returns:
        ExtractionWindow configuration
    """
    complexity = analyze_conversation_complexity(conversation)

    if complexity < 0.3:
        return WINDOW_PRESETS["fast"]
    elif complexity < 0.7:
        return WINDOW_PRESETS["standard"]
    else:
        return WINDOW_PRESETS["deep"]


def analyze_conversation_complexity(
    conversation: List[Dict[str, str]],
) -> float:
    """
    Analyze conversation complexity.

    Indicators:
    1. Entity count (people, places, things)
    2. Relation density (connections between entities)
    3. Temporal span (time references)
    4. Topic switches (changes in subject)

    Returns:
        Complexity score (0-1)
    """
    # Combine all messages
    text = " ".join([msg.get("content", "") for msg in conversation])

    # 1. Entity count
    entity_count = _count_entities(text)
    entity_score = min(entity_count / 10, 1.0)

    # 2. Relation density (heuristic: pronouns, conjunctions)
    relation_density = _calculate_relation_density(text)

    # 3. Temporal span (time references)
    temporal_span = _detect_temporal_references(text)

    # 4. Topic switches
    topic_switches = _detect_topic_switches(conversation)
    topic_score = min(topic_switches / 5, 1.0)

    # Weighted combination
    complexity = (
        0.3 * entity_score +
        0.3 * relation_density +
        0.2 * temporal_span +
        0.2 * topic_score
    )

    return min(complexity, 1.0)


def _count_entities(text: str) -> int:
    """
    Count entities in text (heuristic approach).

    Patterns:
    - Capitalized words (names, places)
    - Numbers (quantities, dates)
    - Quoted strings (specific terms)
    """
    # Capitalized words (not at sentence start)
    capitalized = re.findall(r'(?<!^)(?<!\. )(?<!\! )(?<!\? )[A-Z][a-z]+', text)

    # Numbers
    numbers = re.findall(r'\d+', text)

    # Quoted strings
    quoted = re.findall(r'"([^"]+)"', text)

    # Total entities
    entity_count = len(capitalized) + len(numbers) + len(quoted)

    return entity_count


def _calculate_relation_density(text: str) -> float:
    """
    Calculate relation density based on connecting words.

    Indicators:
    - Pronouns (he, she, it, they) - refer to entities
    - Conjunctions (and, but, or) - connect ideas
    - Prepositions (in, on, at, to) - spatial/temporal relations
    """
    # Pronouns
    pronouns = re.findall(r'\b(he|she|it|they|him|her|them|his|hers|its|their)\b', text, re.I)

    # Conjunctions
    conjunctions = re.findall(r'\b(and|but|or|nor|yet|so)\b', text, re.I)

    # Prepositions
    prepositions = re.findall(r'\b(in|on|at|to|from|with|by|for|of|about)\b', text, re.I)

    # Total connectors
    connectors = len(pronouns) + len(conjunctions) + len(prepositions)

    # Normalize by text length (words)
    word_count = len(text.split())
    if word_count == 0:
        return 0.0

    density = connectors / word_count

    # Cap at 1.0
    return min(density * 10, 1.0)


def _detect_temporal_references(text: str) -> float:
    """
    Detect temporal references in text.

    Patterns:
    - Date patterns (2024-01-01, Jan 1, yesterday, tomorrow)
    - Time patterns (2pm, 14:00, morning, evening)
    - Duration patterns (2 hours, 3 days, a week)
    """
    # Date patterns
    dates = re.findall(
        r'\b(\d{4}-\d{2}-\d{2}|'
        r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
        r'yesterday|tomorrow|today|'
        r'last week|next week|'
        r'last month|next month)\b',
        text,
        re.I
    )

    # Time patterns
    times = re.findall(
        r'\b(\d{1,2}:\d{2}|'
        r'\d{1,2}(am|pm)|'
        r'morning|afternoon|evening|night)\b',
        text,
        re.I
    )

    # Duration patterns
    durations = re.findall(
        r'\b(\d+\s+(?:hour|day|week|month|year)s?|'
        r'a\s+(?:hour|day|week|month|year))\b',
        text,
        re.I
    )

    # Total temporal references
    temporal_count = len(dates) + len(times) + len(durations)

    # Normalize
    return min(temporal_count / 5, 1.0)


def _detect_topic_switches(conversation: List[Dict[str, str]]) -> int:
    """
    Detect topic switches in conversation.

    Heuristic:
    - Look for transition phrases
    - Compare consecutive messages for topic similarity
    """
    transition_phrases = [
        "by the way", "speaking of", "anyway",
        "on another note", "changing topics",
        "let's talk about", "moving on",
        "换个话题", "说到", "另外",
    ]

    switches = 0
    for i, msg in enumerate(conversation):
        content = msg.get("content", "").lower()
        for phrase in transition_phrases:
            if phrase in content:
                switches += 1
                break

    return switches


def get_window_stats(window: ExtractionWindow) -> Dict[str, int]:
    """Get window statistics for logging."""
    return {
        "context_window": window.m,
        "similar_memories": window.s,
        "mode": window.mode,
    }
