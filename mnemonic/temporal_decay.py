"""Temporal Decay Importance Algorithm.

Based on Ebbinghaus forgetting curve: R = e^(-t/S)
Where:
- R: retention rate
- t: time elapsed
- S: memory strength

Extended with access boost: I(t) = I_0 * e^(-λt) * access_boost
"""

import math
from datetime import datetime, timezone
from typing import Dict

# Decay rates for different memory types (λ parameter)
DECAY_RATES: Dict[str, float] = {
    "fact": 0.05,       # Long-term memory (slow decay)
    "preference": 0.1,  # Medium-term memory
    "event": 0.2,       # Short-term memory (fast decay)
    "procedure": 0.03,  # Skill memory (most stable)
}

# Minimum importance threshold (prevent complete forgetting)
MIN_IMPORTANCE_THRESHOLD = 0.1

# Access boost coefficient
ACCESS_BOOST_COEFFICIENT = 0.1


def calculate_temporal_importance(
    initial_importance: float,
    memory_type: str,
    created_at: datetime,
    access_count: int,
    current_time: datetime = None,
) -> float:
    """
    Calculate dynamic importance based on temporal decay and access boost.

    Formula: I(t) = I_0 * e^(-λt) * (1 + α * access_count)

    Args:
        initial_importance: Initial importance score (0-1)
        memory_type: Type of memory (fact/preference/event/procedure)
        created_at: Memory creation timestamp
        access_count: Number of times this memory was accessed
        current_time: Current timestamp (default: now)

    Returns:
        Dynamic importance score (0-1)
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Get decay rate for memory type
    decay_rate = DECAY_RATES.get(memory_type, 0.1)

    # Calculate days elapsed
    days_elapsed = (current_time - created_at).total_seconds() / 86400.0

    # Ebbinghaus decay factor: e^(-λt)
    decay_factor = math.exp(-decay_rate * days_elapsed)

    # Access boost: (1 + α * access_count)
    access_boost = 1 + ACCESS_BOOST_COEFFICIENT * access_count

    # Calculate dynamic importance
    dynamic_importance = initial_importance * decay_factor * access_boost

    # Apply minimum threshold
    dynamic_importance = max(dynamic_importance, MIN_IMPORTANCE_THRESHOLD)

    # Cap at 1.0
    dynamic_importance = min(dynamic_importance, 1.0)

    return dynamic_importance


def get_decay_rate(memory_type: str) -> float:
    """Get decay rate for a memory type."""
    return DECAY_RATES.get(memory_type, 0.1)


def should_compress_memory(
    importance: float,
    days_elapsed: float,
    access_count: int,
) -> bool:
    """
    Determine if a memory should be compressed/summarized.

    Criteria:
    - Importance below threshold (0.2)
    - Not accessed in last 30 days
    - Access count < 3

    Returns:
        True if memory should be compressed
    """
    return (
        importance < 0.2 and
        days_elapsed > 30 and
        access_count < 3
    )


def calculate_importance_boost(access_count: int) -> float:
    """Calculate importance boost from access count."""
    return 1 + ACCESS_BOOST_COEFFICIENT * access_count