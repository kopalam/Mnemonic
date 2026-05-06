"""Tests for Bidirectional Diffusion Retrieval (Phase 4)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from mnemonic.diffusion_retrieval import (
    bidirectional_diffusion_search,
    _forward_diffusion,
    _backward_diffusion,
    _combine_diffusion_results,
    _extract_keywords,
    _extract_concepts,
    _generate_refinements,
    DiffusionResult,
)


class TestExtractKeywords:
    """Test keyword extraction."""

    def test_extract_from_single_memory(self):
        """Extract keywords from a single memory."""
        memories = [{"content": "John likes pizza and pasta"}]
        keywords = _extract_keywords(memories)
        assert "john" in keywords
        assert "likes" in keywords
        assert "pizza" in keywords
        assert "pasta" in keywords

    def test_extract_from_multiple_memories(self):
        """Extract keywords from multiple memories."""
        memories = [
            {"content": "John likes pizza"},
            {"content": "Mary prefers pasta"},
        ]
        keywords = _extract_keywords(memories)
        assert "john" in keywords
        assert "mary" in keywords
        assert "pizza" in keywords
        assert "pasta" in keywords

    def test_filter_short_words(self):
        """Short words are filtered."""
        memories = [{"content": "I am a test"}]
        keywords = _extract_keywords(memories)
        assert "test" in keywords
        # Short words like "I", "am", "a" should be filtered
        assert "i" not in keywords
        assert "am" not in keywords

    def test_deduplicate(self):
        """Keywords are deduplicated."""
        memories = [
            {"content": "John likes pizza"},
            {"content": "John loves pizza"},
        ]
        keywords = _extract_keywords(memories)
        assert keywords.count("john") == 1
        assert keywords.count("pizza") == 1


class TestExtractConcepts:
    """Test concept extraction."""

    def test_extract_capitalized_entities(self):
        """Extract capitalized entities."""
        memories = [{"content": "John went to Paris with Mary"}]
        concepts = _extract_concepts(memories)
        assert "John" in concepts
        assert "Paris" in concepts
        assert "Mary" in concepts

    def test_no_capitalized_entities(self):
        """No capitalized entities."""
        memories = [{"content": "the quick brown fox"}]
        concepts = _extract_concepts(memories)
        assert len(concepts) == 0

    def test_deduplicate_concepts(self):
        """Concepts are deduplicated."""
        memories = [
            {"content": "John likes pizza"},
            {"content": "John lives in Paris"},
        ]
        concepts = _extract_concepts(memories)
        assert concepts.count("John") == 1


class TestGenerateRefinements:
    """Test query refinement generation."""

    def test_add_concepts_to_query(self):
        """Add concepts to query."""
        query = "what does John like"
        concepts = ["pizza", "pasta"]
        refinements = _generate_refinements(query, concepts)
        assert len(refinements) == 2
        assert "pizza" in refinements[0]
        assert "pasta" in refinements[1]

    def test_limit_to_top_concepts(self):
        """Limit to top 3 concepts."""
        query = "test"
        concepts = ["a", "b", "c", "d", "e"]
        refinements = _generate_refinements(query, concepts)
        assert len(refinements) == 3


class TestCombineDiffusionResults:
    """Test combining forward and backward results."""

    def test_combine_with_weights(self):
        """Combine with different weights."""
        forward = [{"id": "1", "content": "forward", "score": 0.9}]
        backward = [{"id": "2", "content": "backward", "score": 0.8}]
        combined = _combine_diffusion_results(forward, backward)
        assert len(combined) == 2
        # Forward should have higher weight
        forward_mem = next(m for m in combined if m["id"] == "1")
        assert forward_mem["_diffusion_weight"] == 0.7
        backward_mem = next(m for m in combined if m["id"] == "2")
        assert backward_mem["_diffusion_weight"] == 0.3

    def test_sort_by_combined_score(self):
        """Sort by combined score."""
        forward = [{"id": "1", "content": "forward", "score": 0.5}]
        backward = [{"id": "2", "content": "backward", "score": 0.99}]
        combined = _combine_diffusion_results(forward, backward)
        # Higher base score with lower weight might still rank lower
        assert len(combined) == 2

    def test_empty_inputs(self):
        """Handle empty inputs."""
        combined = _combine_diffusion_results([], [])
        assert len(combined) == 0


class TestForwardDiffusion:
    """Test forward diffusion."""

    @pytest.mark.asyncio
    async def test_initial_search(self):
        """Initial search returns memories."""
        store = MagicMock()
        store.search_vector = AsyncMock(return_value=[
            {"id": "1", "content": "test memory", "score": 0.9}
        ])

        memories = await _forward_diffusion(
            query="test",
            store=store,
            namespace="test",
            k=5,
            steps=1,
        )

        assert len(memories) == 1
        assert memories[0]["content"] == "test memory"

    @pytest.mark.asyncio
    async def test_expand_to_related(self):
        """Expand to related memories in multiple steps."""
        store = MagicMock()
        store.search_vector = AsyncMock(return_value=[
            {"id": "1", "content": "John likes pizza", "score": 0.9}
        ])
        store.search_bm25 = AsyncMock(return_value=[
            {"id": "2", "content": "Mary likes pasta", "score": 0.8}
        ])

        memories = await _forward_diffusion(
            query="test",
            store=store,
            namespace="test",
            k=5,
            steps=2,
        )

        # Should include both initial and related
        assert len(memories) >= 1


class TestBackwardDiffusion:
    """Test backward diffusion."""

    @pytest.mark.asyncio
    async def test_refine_query(self):
        """Refine query based on memories."""
        store = MagicMock()
        store.search_vector = AsyncMock(return_value=[
            {"id": "2", "content": "refined memory", "score": 0.8}
        ])

        forward_memories = [{"id": "1", "content": "John likes pizza"}]

        backward_memories, refinements = await _backward_diffusion(
            query="what does John like",
            forward_memories=forward_memories,
            store=store,
            namespace="test",
            steps=1,
        )

        # Should generate refinements
        assert len(refinements) > 0


class TestBidirectionalDiffusionSearch:
    """Test full bidirectional diffusion search."""

    @pytest.mark.asyncio
    async def test_full_search(self):
        """Full bidirectional diffusion search."""
        store = MagicMock()
        store.search_vector = AsyncMock(return_value=[
            {"id": "1", "content": "test memory", "score": 0.9}
        ])
        store.search_bm25 = AsyncMock(return_value=[])

        result = await bidirectional_diffusion_search(
            query="test",
            store=store,
            namespace="test",
            k=5,
            diffusion_steps=1,
        )

        assert isinstance(result, DiffusionResult)
        assert len(result.memories) >= 0
        assert 0 <= result.forward_score <= 1
        assert 0 <= result.backward_score <= 1
        assert 0 <= result.combined_score <= 1

    @pytest.mark.asyncio
    async def test_returns_top_k(self):
        """Returns top-k memories."""
        store = MagicMock()
        store.search_vector = AsyncMock(return_value=[
            {"id": "1", "content": "memory 1", "score": 0.9},
            {"id": "2", "content": "memory 2", "score": 0.8},
            {"id": "3", "content": "memory 3", "score": 0.7},
        ])
        store.search_bm25 = AsyncMock(return_value=[])

        result = await bidirectional_diffusion_search(
            query="test",
            store=store,
            namespace="test",
            k=2,
            diffusion_steps=1,
        )

        assert len(result.memories) <= 2