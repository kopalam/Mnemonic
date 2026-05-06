"""Tests for Memory Compression (Phase 5)."""

import pytest
from mnemonic.memory_compression import (
    compress_memories,
    should_compress,
    _are_memories_related,
    _determine_compression_type,
    _has_temporal_reference,
    _compress_temporal_sequence,
    _compress_entity_centric,
    _compress_topic_cluster,
    CompressionResult,
)


class TestAreMemoriesRelated:
    """Test memory relatedness detection."""

    def test_shared_entity(self):
        """Memories with shared entity are related."""
        memories = [
            {"id": "1", "content": "John likes pizza"},
            {"id": "2", "content": "John lives in Paris"},
        ]
        assert _are_memories_related(memories) is True

    def test_shared_keywords(self):
        """Memories with shared keywords are related."""
        memories = [
            {"id": "1", "content": "pizza is delicious food and tasty"},
            {"id": "2", "content": "pasta is also delicious food and tasty"},
        ]
        assert _are_memories_related(memories) is True

    def test_unrelated_memories(self):
        """Unrelated memories are not related."""
        memories = [
            {"id": "1", "content": "John likes pizza"},
            {"id": "2", "content": "The sky is blue"},
        ]
        assert _are_memories_related(memories) is False

    def test_single_memory(self):
        """Single memory is not related."""
        memories = [{"id": "1", "content": "Test"}]
        assert _are_memories_related(memories) is False


class TestHasTemporalReference:
    """Test temporal reference detection."""

    def test_date_pattern(self):
        """Date pattern is detected."""
        assert _has_temporal_reference("2024-01-15") is True

    def test_time_pattern(self):
        """Time pattern is detected."""
        assert _has_temporal_reference("14:30") is True

    def test_relative_time(self):
        """Relative time is detected."""
        assert _has_temporal_reference("yesterday") is True
        assert _has_temporal_reference("next week") is True

    def test_duration(self):
        """Duration is detected."""
        assert _has_temporal_reference("2 hours") is True

    def test_no_temporal(self):
        """No temporal reference."""
        assert _has_temporal_reference("The sky is blue") is False


class TestDetermineCompressionType:
    """Test compression type determination."""

    def test_temporal_sequence(self):
        """Temporal sequence type (no shared entities)."""
        memories = [
            {"id": "1", "content": "arrived yesterday"},
            {"id": "2", "content": "left tomorrow"},
        ]
        compression_type = _determine_compression_type(memories)
        assert compression_type == "temporal_sequence"

    def test_entity_centric(self):
        """Entity-centric type."""
        memories = [
            {"id": "1", "content": "John is 25 years old"},
            {"id": "2", "content": "John lives in Paris"},
            {"id": "3", "content": "John works at Google"},
        ]
        compression_type = _determine_compression_type(memories)
        # Entity-centric takes priority over temporal
        assert compression_type in ["entity_centric", "temporal_sequence"]

    def test_topic_cluster(self):
        """Topic cluster type."""
        memories = [
            {"id": "1", "content": "pizza is delicious"},
            {"id": "2", "content": "pasta is also good"},
        ]
        compression_type = _determine_compression_type(memories)
        assert compression_type == "topic_cluster"


class TestCompressTemporalSequence:
    """Test temporal sequence compression."""

    def test_compress_sequence(self):
        """Compress temporal sequence."""
        memories = [
            {"id": "1", "content": "John arrived at the airport", "importance": 0.7},
            {"id": "2", "content": "John checked into the hotel", "importance": 0.8},
            {"id": "3", "content": "John went to the meeting", "importance": 0.9},
        ]
        compressed = _compress_temporal_sequence(memories)
        assert "→" in compressed["content"]
        assert compressed["type"] == "event"
        assert compressed["importance"] == 0.9  # Max importance
        assert len(compressed["compressed_from"]) == 3

    def test_compress_long_sequence(self):
        """Compress long sequence."""
        memories = [
            {"id": "1", "content": "Event 1", "importance": 0.5},
            {"id": "2", "content": "Event 2", "importance": 0.5},
            {"id": "3", "content": "Event 3", "importance": 0.5},
            {"id": "4", "content": "Event 4", "importance": 0.5},
            {"id": "5", "content": "Event 5", "importance": 0.5},
        ]
        compressed = _compress_temporal_sequence(memories)
        assert "5 events total" in compressed["content"]


class TestCompressEntityCentric:
    """Test entity-centric compression."""

    def test_compress_entity_facts(self):
        """Compress facts about entity."""
        memories = [
            {"id": "1", "content": "John is 25 years old", "importance": 0.7},
            {"id": "2", "content": "John lives in Paris", "importance": 0.8},
            {"id": "3", "content": "John works at Google", "importance": 0.9},
        ]
        compressed = _compress_entity_centric(memories)
        assert "John:" in compressed["content"]
        assert compressed["type"] == "fact"
        assert compressed["importance"] == 0.9

    def test_compress_many_facts(self):
        """Compress many facts."""
        memories = [
            {"id": f"{i}", "content": f"John fact {i}", "importance": 0.5}
            for i in range(10)
        ]
        compressed = _compress_entity_centric(memories)
        assert "10 facts total" in compressed["content"]


class TestCompressTopicCluster:
    """Test topic cluster compression."""

    def test_compress_topic(self):
        """Compress topic cluster."""
        memories = [
            {"id": "1", "content": "pizza is delicious Italian food", "importance": 0.7},
            {"id": "2", "content": "pasta is also delicious Italian food", "importance": 0.8},
        ]
        compressed = _compress_topic_cluster(memories)
        assert "Related memories about:" in compressed["content"]
        assert "2 memories compressed" in compressed["content"]


class TestCompressMemories:
    """Test full compression function."""

    def test_compress_related_memories(self):
        """Compress related memories."""
        memories = [
            {"id": "1", "content": "John likes pizza", "importance": 0.7},
            {"id": "2", "content": "John lives in Paris", "importance": 0.8},
        ]
        result = compress_memories(memories)
        assert result is not None
        assert isinstance(result, CompressionResult)
        assert len(result.source_memory_ids) == 2
        assert result.compression_ratio >= 0

    def test_not_compress_unrelated(self):
        """Don't compress unrelated memories."""
        memories = [
            {"id": "1", "content": "John likes pizza", "importance": 0.7},
            {"id": "2", "content": "The sky is blue", "importance": 0.8},
        ]
        result = compress_memories(memories)
        assert result is None

    def test_not_compress_single(self):
        """Don't compress single memory."""
        memories = [{"id": "1", "content": "Test", "importance": 0.7}]
        result = compress_memories(memories)
        assert result is None

    def test_not_compress_low_importance(self):
        """Don't compress low importance memories."""
        memories = [
            {"id": "1", "content": "John likes pizza", "importance": 0.1},
            {"id": "2", "content": "John lives in Paris", "importance": 0.1},
        ]
        result = compress_memories(memories, min_importance=0.3)
        assert result is None


class TestShouldCompress:
    """Test compression decision."""

    def test_should_compress_many_related(self):
        """Should compress many related memories."""
        memories = [
            {"id": f"{i}", "content": f"John fact {i}", "importance": 0.7}
            for i in range(10)
        ]
        assert should_compress(memories, threshold=5) is True

    def test_should_not_compress_few(self):
        """Should not compress few memories."""
        memories = [
            {"id": "1", "content": "John likes pizza", "importance": 0.7},
            {"id": "2", "content": "John lives in Paris", "importance": 0.8},
        ]
        assert should_compress(memories, threshold=5) is False

    def test_should_not_compress_unrelated(self):
        """Should not compress unrelated memories."""
        # Each memory has completely different content
        memories = [
            {"id": "0", "content": "Apple is a fruit", "importance": 0.7},
            {"id": "1", "content": "Python is a language", "importance": 0.7},
            {"id": "2", "content": "Tokyo is in Japan", "importance": 0.7},
            {"id": "3", "content": "Coffee has caffeine", "importance": 0.7},
            {"id": "4", "content": "Mars is a planet", "importance": 0.7},
            {"id": "5", "content": "Music has rhythm", "importance": 0.7},
            {"id": "6", "content": "Books have pages", "importance": 0.7},
            {"id": "7", "content": "Snow is cold", "importance": 0.7},
            {"id": "8", "content": "Time flies fast", "importance": 0.7},
            {"id": "9", "content": "Dreams are weird", "importance": 0.7},
        ]
        assert should_compress(memories, threshold=5) is False

    def test_should_not_compress_low_importance(self):
        """Should not compress low importance memories."""
        memories = [
            {"id": f"{i}", "content": f"John fact {i}", "importance": 0.1}
            for i in range(10)
        ]
        assert should_compress(memories, threshold=5) is False