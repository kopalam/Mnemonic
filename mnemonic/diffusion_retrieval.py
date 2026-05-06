"""Bidirectional Diffusion Retrieval Algorithm.

Based on IGMiRAG's bidirectional diffusion concept.
Forward diffusion: query → related memories
Backward diffusion: memories → query refinement
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class DiffusionResult:
    """Result of bidirectional diffusion retrieval."""
    memories: List[Dict]
    forward_score: float
    backward_score: float
    combined_score: float
    refinement_suggestions: List[str]


async def bidirectional_diffusion_search(
    query: str,
    store,
    namespace: str,
    k: int = 10,
    diffusion_steps: int = 2,
) -> DiffusionResult:
    """
    Perform bidirectional diffusion retrieval.

    Args:
        query: Search query
        store: MemoryStore instance
        namespace: Memory namespace
        k: Number of memories to retrieve
        diffusion_steps: Number of diffusion steps

    Returns:
        DiffusionResult with memories and scores
    """
    # Step 1: Forward diffusion (query → memories)
    forward_memories = await _forward_diffusion(
        query, store, namespace, k, diffusion_steps
    )

    # Step 2: Backward diffusion (memories → query refinement)
    backward_memories, refinement_suggestions = await _backward_diffusion(
        query, forward_memories, store, namespace, diffusion_steps
    )

    # Step 3: Combine and rank
    combined_memories = _combine_diffusion_results(
        forward_memories, backward_memories
    )

    # Step 4: Calculate scores
    forward_score = _calculate_diffusion_score(forward_memories)
    backward_score = _calculate_diffusion_score(backward_memories)
    combined_score = (forward_score + backward_score) / 2

    # Step 5: Return top-k
    top_memories = combined_memories[:k]

    return DiffusionResult(
        memories=top_memories,
        forward_score=forward_score,
        backward_score=backward_score,
        combined_score=combined_score,
        refinement_suggestions=refinement_suggestions,
    )


async def _forward_diffusion(
    query: str,
    store,
    namespace: str,
    k: int,
    steps: int,
) -> List[Dict]:
    """
    Forward diffusion: query → related memories.

    Process:
    1. Initial search
    2. For each step, expand to related memories
    """
    # Initial search
    initial_memories = await store.search_vector(
        namespace=namespace,
        query=query,
        limit=k,
    )

    if steps == 1:
        return initial_memories

    # Expand to related memories
    all_memories = list(initial_memories)
    seen_ids = {m.get("id") for m in all_memories}

    for step in range(steps - 1):
        # Get keywords from current memories
        keywords = _extract_keywords(all_memories)

        # Search for each keyword
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            related = await store.search_bm25(
                namespace=namespace,
                query=keyword,
                limit=k // 2,
            )

            for mem in related:
                if mem.get("id") not in seen_ids:
                    all_memories.append(mem)
                    seen_ids.add(mem.get("id"))

    return all_memories


async def _backward_diffusion(
    query: str,
    forward_memories: List[Dict],
    store,
    namespace: str,
    steps: int,
) -> Tuple[List[Dict], List[str]]:
    """
    Backward diffusion: memories → query refinement.

    Process:
    1. Extract key concepts from memories
    2. Generate refined queries
    3. Search with refined queries
    """
    # Extract key concepts
    concepts = _extract_concepts(forward_memories)

    # Generate refinement suggestions
    refinement_suggestions = _generate_refinements(query, concepts)

    # Search with refined queries
    backward_memories = []

    for refinement in refinement_suggestions[:2]:  # Limit to top 2 refinements
        refined_memories = await store.search_vector(
            namespace=namespace,
            query=refinement,
            limit=5,
        )
        backward_memories.extend(refined_memories)

    # Deduplicate
    seen_ids = {m.get("id") for m in forward_memories}
    unique_backward = [
        m for m in backward_memories
        if m.get("id") not in seen_ids
    ]

    return unique_backward, refinement_suggestions


def _combine_diffusion_results(
    forward_memories: List[Dict],
    backward_memories: List[Dict],
) -> List[Dict]:
    """
    Combine forward and backward diffusion results.

    Strategy:
    - Forward memories get higher weight (0.7)
    - Backward memories get lower weight (0.3)
    - Re-rank by combined score
    """
    combined = []

    # Add forward memories with weight
    for mem in forward_memories:
        mem_copy = mem.copy()
        mem_copy["_diffusion_weight"] = 0.7
        mem_copy["_diffusion_source"] = "forward"
        combined.append(mem_copy)

    # Add backward memories with weight
    for mem in backward_memories:
        mem_copy = mem.copy()
        mem_copy["_diffusion_weight"] = 0.3
        mem_copy["_diffusion_source"] = "backward"
        combined.append(mem_copy)

    # Sort by combined score
    def sort_key(mem):
        base_score = mem.get("score", 0.5)
        weight = mem.get("_diffusion_weight", 0.5)
        return base_score * weight

    combined.sort(key=sort_key, reverse=True)

    return combined


def _extract_keywords(memories: List[Dict]) -> List[str]:
    """Extract keywords from memories."""
    keywords = []

    for mem in memories:
        content = mem.get("content", "")
        # Simple keyword extraction: split by spaces, filter short words
        words = content.split()
        for word in words:
            if len(word) > 3:  # Filter short words
                keywords.append(word.lower())

    # Deduplicate and return
    return list(set(keywords))


def _extract_concepts(memories: List[Dict]) -> List[str]:
    """Extract key concepts from memories."""
    concepts = []

    for mem in memories:
        content = mem.get("content", "")
        # Extract entities (capitalized words)
        import re
        entities = re.findall(r'\b[A-Z][a-z]+\b', content)
        concepts.extend(entities)

    # Deduplicate and return
    return list(set(concepts))


def _generate_refinements(
    query: str,
    concepts: List[str],
) -> List[str]:
    """Generate query refinements based on concepts."""
    refinements = []

    # Add top concepts to query
    for concept in concepts[:3]:
        refinement = f"{query} {concept}"
        refinements.append(refinement)

    return refinements


def _calculate_diffusion_score(memories: List[Dict]) -> float:
    """Calculate average score for diffusion results."""
    if not memories:
        return 0.0

    scores = [m.get("score", 0.5) for m in memories]
    return sum(scores) / len(scores)
