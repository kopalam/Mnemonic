"""Tests for Temporal Decay Importance Algorithm."""

import pytest
from datetime import datetime, timezone, timedelta
from mnemonic.temporal_decay import (
    calculate_temporal_importance,
    get_decay_rate,
    should_compress_memory,
    DECAY_RATES,
    MIN_IMPORTANCE_THRESHOLD,
)


class TestTemporalDecay:
    """Test temporal decay importance calculation."""

    def test_decay_rates_defined(self):
        """Test that decay rates are properly defined."""
        assert "fact" in DECAY_RATES
        assert "preference" in DECAY_RATES
        assert "event" in DECAY_RATES
        assert "procedure" in DECAY_RATES

        # Fact should decay slowest
        assert DECAY_RATES["fact"] < DECAY_RATES["preference"]
        assert DECAY_RATES["preference"] < DECAY_RATES["event"]
        assert DECAY_RATES["procedure"] < DECAY_RATES["fact"]

    def test_calculate_importance_new_memory(self):
        """Test importance for newly created memory."""
        now = datetime.now(timezone.utc)
        importance = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="fact",
            created_at=now,
            access_count=0,
        )

        # New memory should have full importance
        assert importance == pytest.approx(0.5, rel=0.01)

    def test_calculate_importance_old_memory(self):
        """Test importance decay over time."""
        # Memory created 30 days ago
        created = datetime.now(timezone.utc) - timedelta(days=30)

        importance = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="event",  # Fast decay
            created_at=created,
            access_count=0,
        )

        # Should decay significantly
        assert importance < 0.5
        # Event with λ=0.2 over 30 days: 0.5 * e^(-6) ≈ 0.001, capped at 0.1
        assert importance >= MIN_IMPORTANCE_THRESHOLD

    def test_calculate_importance_access_boost(self):
        """Test that access count boosts importance."""
        now = datetime.now(timezone.utc)

        importance_no_access = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="fact",
            created_at=now,
            access_count=0,
        )

        importance_with_access = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="fact",
            created_at=now,
            access_count=10,  # Accessed 10 times
        )

        # More access should boost importance
        assert importance_with_access > importance_no_access

    def test_minimum_threshold(self):
        """Test that importance never goes below minimum threshold."""
        # Memory created 365 days ago (very old)
        created = datetime.now(timezone.utc) - timedelta(days=365)

        importance = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="event",  # Fastest decay
            created_at=created,
            access_count=0,
        )

        # Should be at minimum threshold
        assert importance >= MIN_IMPORTANCE_THRESHOLD

    def test_importance_capped_at_one(self):
        """Test that importance is capped at 1.0."""
        now = datetime.now(timezone.utc)

        # Very high access count
        importance = calculate_temporal_importance(
            initial_importance=1.0,
            memory_type="fact",
            created_at=now,
            access_count=100,
        )

        # Should not exceed 1.0
        assert importance <= 1.0

    def test_different_memory_types(self):
        """Test different decay rates for memory types."""
        created = datetime.now(timezone.utc) - timedelta(days=10)

        importance_fact = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="fact",
            created_at=created,
            access_count=0,
        )

        importance_event = calculate_temporal_importance(
            initial_importance=0.5,
            memory_type="event",
            created_at=created,
            access_count=0,
        )

        # Fact should retain more importance than event
        assert importance_fact > importance_event

    def test_should_compress_memory(self):
        """Test memory compression decision."""
        # Low importance, old, not accessed
        assert should_compress_memory(
            importance=0.15,
            days_elapsed=35,
            access_count=2,
        ) is True

        # High importance
        assert should_compress_memory(
            importance=0.5,
            days_elapsed=35,
            access_count=2,
        ) is False

        # Frequently accessed
        assert should_compress_memory(
            importance=0.15,
            days_elapsed=35,
            access_count=10,
        ) is False

        # Recently accessed
        assert should_compress_memory(
            importance=0.15,
            days_elapsed=5,
            access_count=2,
        ) is False

    def test_get_decay_rate(self):
        """Test decay rate retrieval."""
        assert get_decay_rate("fact") == 0.05
        assert get_decay_rate("preference") == 0.1
        assert get_decay_rate("event") == 0.2
        assert get_decay_rate("procedure") == 0.03

        # Unknown type should use default
        assert get_decay_rate("unknown") == 0.1


class TestTemporalDecayIntegration:
    """Integration tests with database models."""

    @pytest.mark.asyncio
    async def test_memory_access_count_update(self):
        """Test that access_count is updated on retrieval."""
        # This test requires database setup
        # Will be implemented in integration tests
        pass

    @pytest.mark.asyncio
    async def test_dynamic_importance_in_search(self):
        """Test that dynamic importance is calculated in search."""
        # This test requires database setup
        # Will be implemented in integration tests
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])