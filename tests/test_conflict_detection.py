"""Tests for Conflict Detection and Merge (Phase 3)."""

import pytest
from mnemonic.conflict_detection import (
    detect_conflict,
    resolve_conflict,
    detect_all_conflicts,
    ConflictType,
    Conflict,
    _calculate_similarity,
    _is_contradiction,
    _is_update,
    _merge_memories,
)


class TestCalculateSimilarity:
    """Test text similarity calculation."""

    def test_identical_texts(self):
        """Identical texts have similarity 1.0."""
        text = "The quick brown fox"
        similarity = _calculate_similarity(text, text)
        assert similarity == 1.0

    def test_completely_different_texts(self):
        """Completely different texts have similarity 0.0."""
        text_1 = "apple banana cherry"
        text_2 = "dog elephant fox"
        similarity = _calculate_similarity(text_1, text_2)
        assert similarity == 0.0

    def test_partial_overlap(self):
        """Partially overlapping texts have similarity between 0 and 1."""
        text_1 = "apple banana cherry"
        text_2 = "banana cherry dog"
        similarity = _calculate_similarity(text_1, text_2)
        assert 0 < similarity < 1

    def test_empty_texts(self):
        """Empty texts have similarity 0.0."""
        similarity = _calculate_similarity("", "")
        assert similarity == 0.0


class TestIsContradiction:
    """Test contradiction detection."""

    def test_likes_dislikes_contradiction(self):
        """Likes vs dislikes is a contradiction."""
        text_1 = "John likes pizza"
        text_2 = "John dislikes pizza"
        assert _is_contradiction(text_1, text_2) is True

    def test_is_is_not_contradiction(self):
        """Is vs is not is a contradiction."""
        text_1 = "The store is open"
        text_2 = "The store is not open"
        assert _is_contradiction(text_1, text_2) is True

    def test_no_contradiction(self):
        """No contradiction."""
        text_1 = "John likes pizza"
        text_2 = "John lives in Paris"
        assert _is_contradiction(text_1, text_2) is False


class TestIsUpdate:
    """Test update detection."""

    def test_same_entity_different_value(self):
        """Same entity with different value is an update."""
        memory_1 = {"content": "John's age is 25"}
        memory_2 = {"content": "John's age is 26"}
        assert _is_update(memory_1, memory_2) is True

    def test_different_entities(self):
        """Different entities are not an update."""
        memory_1 = {"content": "John's age is 25"}
        memory_2 = {"content": "Mary's age is 30"}
        assert _is_update(memory_1, memory_2) is False


class TestDetectConflict:
    """Test conflict detection."""

    def test_duplicate_detection(self):
        """Detect duplicate memories."""
        memory_1 = {"id": "1", "content": "John likes pizza"}
        memory_2 = {"id": "2", "content": "John likes pizza"}
        conflict_type = detect_conflict(memory_1, memory_2)
        assert conflict_type == ConflictType.DUPLICATE

    def test_contradiction_detection(self):
        """Detect contradictory memories."""
        memory_1 = {"id": "1", "content": "John likes pizza"}
        memory_2 = {"id": "2", "content": "John dislikes pizza"}
        conflict_type = detect_conflict(memory_1, memory_2)
        assert conflict_type == ConflictType.CONTRADICTION

    def test_complementary_detection(self):
        """Detect complementary memories."""
        memory_1 = {"id": "1", "content": "John works at Google"}
        memory_2 = {"id": "2", "content": "John works at Google as an engineer"}
        conflict_type = detect_conflict(memory_1, memory_2)
        # High similarity should be complementary
        assert conflict_type in [ConflictType.COMPLEMENTARY, ConflictType.DUPLICATE]

    def test_no_conflict(self):
        """No conflict between unrelated memories."""
        memory_1 = {"id": "1", "content": "John likes pizza"}
        memory_2 = {"id": "2", "content": "Mary lives in Paris"}
        conflict_type = detect_conflict(memory_1, memory_2)
        assert conflict_type == ConflictType.NONE


class TestResolveConflict:
    """Test conflict resolution."""

    def test_resolve_duplicate(self):
        """Resolve duplicate by keeping newer."""
        memory_1 = {"id": "1", "content": "John likes pizza", "access_count": 5}
        memory_2 = {"id": "2", "content": "John likes pizza", "access_count": 3}
        conflict = Conflict(
            type=ConflictType.DUPLICATE,
            memory_id_1="1",
            memory_id_2="2",
            reason="Duplicate memories",
        )
        resolved = resolve_conflict(conflict, memory_1, memory_2)
        assert resolved["access_count"] == 8  # Combined
        assert conflict.resolution == "kept_newer_duplicate"

    def test_resolve_contradiction(self):
        """Resolve contradiction by keeping newer."""
        memory_1 = {"id": "1", "content": "John likes pizza"}
        memory_2 = {"id": "2", "content": "John dislikes pizza"}
        conflict = Conflict(
            type=ConflictType.CONTRADICTION,
            memory_id_1="1",
            memory_id_2="2",
            reason="Contradictory memories",
        )
        resolved = resolve_conflict(conflict, memory_1, memory_2)
        assert resolved["content"] == "John dislikes pizza"
        assert resolved["supersedes"] == "1"
        assert conflict.resolution == "kept_newer_contradiction"

    def test_resolve_update(self):
        """Resolve update by merging."""
        memory_1 = {"id": "1", "content": "John's age is 25", "importance": 0.7, "access_count": 2}
        memory_2 = {"id": "2", "content": "John's age is 26", "importance": 0.8, "access_count": 1}
        conflict = Conflict(
            type=ConflictType.UPDATE,
            memory_id_1="1",
            memory_id_2="2",
            reason="Update memory",
        )
        resolved = resolve_conflict(conflict, memory_1, memory_2)
        assert "previously" in resolved["content"]
        assert resolved["access_count"] == 3
        assert resolved["importance"] == 0.8  # Higher importance
        assert conflict.resolution == "merged_update"


class TestDetectAllConflicts:
    """Test detecting all conflicts in a list."""

    def test_no_conflicts(self):
        """No conflicts in unrelated memories."""
        memories = [
            {"id": "1", "content": "John likes pizza"},
            {"id": "2", "content": "Mary lives in Paris"},
            {"id": "3", "content": "The sky is blue"},
        ]
        conflicts = detect_all_conflicts(memories)
        assert len(conflicts) == 0

    def test_one_conflict(self):
        """One conflict detected."""
        memories = [
            {"id": "1", "content": "John likes pizza"},
            {"id": "2", "content": "John dislikes pizza"},
        ]
        conflicts = detect_all_conflicts(memories)
        assert len(conflicts) == 1
        assert conflicts[0].type == ConflictType.CONTRADICTION

    def test_multiple_conflicts(self):
        """Multiple conflicts detected."""
        memories = [
            {"id": "1", "content": "John likes pizza"},
            {"id": "2", "content": "John likes pizza"},  # Duplicate of 1
            {"id": "3", "content": "Mary lives in Paris"},
            {"id": "4", "content": "Mary lives in Paris"},  # Duplicate of 3
        ]
        conflicts = detect_all_conflicts(memories)
        assert len(conflicts) >= 2


class TestMergeMemories:
    """Test memory merging."""

    def test_merge_combines_content(self):
        """Merge combines content."""
        memory_1 = {"id": "1", "content": "John's age is 25"}
        memory_2 = {"id": "2", "content": "John's age is 26"}
        merged = _merge_memories(memory_1, memory_2)
        assert "previously" in merged["content"]

    def test_merge_sums_access_counts(self):
        """Merge sums access counts."""
        memory_1 = {"id": "1", "content": "Test", "access_count": 5}
        memory_2 = {"id": "2", "content": "Test updated", "access_count": 3}
        merged = _merge_memories(memory_1, memory_2)
        assert merged["access_count"] == 8

    def test_merge_keeps_higher_importance(self):
        """Merge keeps higher importance."""
        memory_1 = {"id": "1", "content": "Test", "importance": 0.9}
        memory_2 = {"id": "2", "content": "Test updated", "importance": 0.5}
        merged = _merge_memories(memory_1, memory_2)
        assert merged["importance"] == 0.9

    def test_merge_tracks_history(self):
        """Merge tracks merge history."""
        memory_1 = {"id": "1", "content": "Test"}
        memory_2 = {"id": "2", "content": "Test updated"}
        merged = _merge_memories(memory_1, memory_2)
        assert "merged_from" in merged
        assert "1" in merged["merged_from"]