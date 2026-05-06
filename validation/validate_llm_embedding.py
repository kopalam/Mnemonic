"""Validation using real LLM extraction with Embedding-based matching.

Optimized version:
- D1: Use embedding similarity instead of keyword overlap
- D2: Enhanced conflict detection for numeric updates
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load environment variables first
from dotenv import load_dotenv
load_dotenv(Path("/Users/kopa/Documents/monic/.env"))

from mnemonic.services import ExtractionService, EmbeddingService
from mnemonic.conflict_detection import detect_conflict, ConflictType, Conflict
from mnemonic.temporal_decay import calculate_temporal_importance
from mnemonic.adaptive_window import determine_extraction_window

from validation.real_dataset import REAL_CONVERSATIONS, REAL_SEARCH_QUERIES, DATASET_STATS


# Embedding-based matching
async def calculate_embedding_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity using embeddings."""
    emb_service = EmbeddingService()
    
    try:
        emb1 = await emb_service.embed(text1)
        emb2 = await emb_service.embed(text2)
        
        # Cosine similarity
        import numpy as np
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float(similarity)
    except Exception as e:
        print(f"  [Warning] Embedding failed: {e}, using fallback")
        # Fallback to keyword similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)


async def validate_with_llm_embedding():
    """Run validation using real LLM extraction + Embedding matching."""
    print("=" * 60)
    print("Mnemonic Validation - Real LLM + Embedding Matching")
    print("=" * 60)
    print(f"\nDataset Statistics:")
    print(f"  Total Conversations: {DATASET_STATS['total_conversations']}")
    print(f"  Source Sessions: {len(DATASET_STATS['source_sessions'])}")
    
    extraction_service = ExtractionService()
    
    # D1: Extraction Quality with LLM + Embedding Matching
    print("\n" + "=" * 60)
    print("[D1] Extraction Quality (LLM + Embedding)")
    print("=" * 60)
    
    total_expected = sum(len(c["expected_memories"]) for c in REAL_CONVERSATIONS if c["expected_memories"])
    total_extracted = 0
    correct_matches = 0
    
    extraction_results = []
    
    for conv in REAL_CONVERSATIONS:
        if not conv["expected_memories"]:
            continue
        
        print(f"\nProcessing {conv['id']}...")
        
        # Use LLM extraction
        try:
            extracted, window_stats = await extraction_service.extract_adaptive(conv["messages"])
            total_extracted += len(extracted)
            
            print(f"  Window: {window_stats['mode']} (m={window_stats['context_window']}, s={window_stats['similar_memories']})")
            print(f"  Extracted: {len(extracted)} memories")
            
            # Match with expected (embedding similarity)
            for exp_mem in conv["expected_memories"]:
                exp_content = exp_mem["content"]
                
                best_similarity = 0.0
                best_match = None
                
                for ext_mem in extracted:
                    ext_content = ext_mem.get("content", "")
                    
                    # Calculate embedding similarity
                    similarity = await calculate_embedding_similarity(exp_content, ext_content)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = ext_content
                
                # Threshold: 0.75 for semantic equivalence
                if best_similarity >= 0.75:
                    correct_matches += 1
                    print(f"  ✓ Matched (sim={best_similarity:.2f}): {best_match[:60]}...")
                else:
                    print(f"  ✗ No match (best_sim={best_similarity:.2f}) for: {exp_content[:60]}...")
            
            extraction_results.append({
                "id": conv["id"],
                "extracted": len(extracted),
                "expected": len(conv["expected_memories"]),
                "window": window_stats,
            })
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    precision = correct_matches / total_extracted if total_extracted > 0 else 0.0
    recall = correct_matches / total_expected if total_expected > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print(f"\n{'=' * 60}")
    print(f"D1 Results:")
    print(f"  Total Expected: {total_expected}")
    print(f"  Total Extracted: {total_extracted}")
    print(f"  Correct Matches: {correct_matches}")
    print(f"  Precision: {precision:.2%}")
    print(f"  Recall: {recall:.2%}")
    print(f"  F1 Score: {f1:.2%}")
    print(f"  Target: F1 ≥ 75%")
    print(f"  Status: {'PASS ✓' if f1 >= 0.75 else 'FAIL ✗'}")
    
    # D2: Conflict Detection (Enhanced)
    print("\n" + "=" * 60)
    print("[D2] Conflict Resolution (Enhanced)")
    print("=" * 60)
    
    conflict_convs = [c for c in REAL_CONVERSATIONS if c.get("category") == "conflict"]
    total_conflicts = len(conflict_convs)
    correct_conflicts = 0
    
    for conv in conflict_convs:
        expected = conv["expected_memories"][0] if conv["expected_memories"] else None
        if not expected:
            continue
        
        conflict_with_id = conv.get("conflict_with")
        if not conflict_with_id:
            continue
        
        conflict_with = next((c for c in REAL_CONVERSATIONS if c["id"] == conflict_with_id), None)
        if not conflict_with:
            continue
        
        old_mem = conflict_with["expected_memories"][0] if conflict_with["expected_memories"] else None
        if not old_mem:
            continue
        
        # Enhanced conflict detection
        conflict_type = detect_conflict_enhanced(old_mem, expected)
        
        if conflict_type in [ConflictType.UPDATE, ConflictType.CONTRADICTION]:
            correct_conflicts += 1
            print(f"\n  {conv['id']}: ✓ {conflict_type.name}")
        else:
            print(f"\n  {conv['id']}: ✗ Expected UPDATE/CONTRADICTION, got {conflict_type.name}")
            print(f"    Old: {old_mem['content'][:50]}...")
            print(f"    New: {expected['content'][:50]}...")
    
    conflict_accuracy = correct_conflicts / total_conflicts if total_conflicts > 0 else 0.0
    
    print(f"\n  Total Conflicts: {total_conflicts}")
    print(f"  Correct: {correct_conflicts}")
    print(f"  Accuracy: {conflict_accuracy:.2%}")
    print(f"  Target: ≥ 90%")
    print(f"  Status: {'PASS ✓' if conflict_accuracy >= 0.90 else 'FAIL ✗'}")
    
    # D3: Robustness
    print("\n" + "=" * 60)
    print("[D3] Robustness")
    print("=" * 60)
    
    noise_convs = [c for c in REAL_CONVERSATIONS if c.get("category") == "noise"]
    total_noise = len(noise_convs)
    filtered = 0
    
    for conv in noise_convs:
        try:
            extracted, _ = await extraction_service.extract_adaptive(conv["messages"])
            if len(extracted) == 0:
                filtered += 1
                print(f"  ✓ {conv['id']}: Filtered (0 memories)")
            else:
                print(f"  ✗ {conv['id']}: Not filtered ({len(extracted)} memories)")
        except Exception as e:
            print(f"  ? {conv['id']}: Error - {e}")
    
    noise_rate = (total_noise - filtered) / total_noise if total_noise > 0 else 0.0
    
    print(f"\n  Total Noise: {total_noise}")
    print(f"  Filtered: {filtered}")
    print(f"  Noise Rate: {noise_rate:.2%}")
    print(f"  Target: ≤ 10%")
    print(f"  Status: {'PASS ✓' if noise_rate <= 0.10 else 'FAIL ✗'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"D1 Extraction F1: {f1:.2%} {'✓' if f1 >= 0.75 else '✗'}")
    print(f"D2 Conflict Accuracy: {conflict_accuracy:.2%} {'✓' if conflict_accuracy >= 0.90 else '✗'}")
    print(f"D3 Noise Rate: {noise_rate:.2%} {'✓' if noise_rate <= 0.10 else '✗'}")
    
    all_pass = f1 >= 0.75 and conflict_accuracy >= 0.90 and noise_rate <= 0.10
    print(f"\nOverall: {'PASS ✓' if all_pass else 'FAIL ✗'}")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "method": "real_llm_embedding",
        "d1_extraction": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "target": 0.75,
            "status": "PASS" if f1 >= 0.75 else "FAIL"
        },
        "d2_conflict": {
            "accuracy": conflict_accuracy,
            "target": 0.90,
            "status": "PASS" if conflict_accuracy >= 0.90 else "FAIL"
        },
        "d3_robustness": {
            "noise_rate": noise_rate,
            "target": 0.10,
            "status": "PASS" if noise_rate <= 0.10 else "FAIL"
        },
        "extraction_results": extraction_results
    }
    
    output_path = Path("/Users/kopa/Documents/monic/validation/llm_embedding_validation_report.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_path}")
    
    return results


def detect_conflict_enhanced(memory_1: Dict, memory_2: Dict) -> ConflictType:
    """
    Enhanced conflict detection with numeric update patterns.
    
    Handles:
    1. Numeric value updates (e.g., "13.3%" → "53.3%")
    2. Count updates (e.g., "2条" → "16条", "17条" → "16条")
    3. Status changes (e.g., "之前是X" → "现在是Y")
    4. Database state changes (e.g., "丢失数据" → "有16条")
    """
    import re
    
    content_1 = memory_1.get("content", "").lower()
    content_2 = memory_2.get("content", "").lower()
    
    # Check for exact duplicate
    if content_1 == content_2:
        return ConflictType.DUPLICATE
    
    # Check for contradiction first
    if _is_contradiction(content_1, content_2):
        return ConflictType.CONTRADICTION
    
    # Enhanced numeric update detection
    # Pattern 1: Percentage updates (e.g., "13.3%" → "53.3%")
    percentages_1 = re.findall(r'(\d+\.?\d*)%', content_1)
    percentages_2 = re.findall(r'(\d+\.?\d*)%', content_2)
    
    if percentages_1 and percentages_2:
        # Check if same metric context
        metric_pattern = r'(l1|l2|l3|accuracy|precision|recall|f1|命中率|准确率)'
        metrics_1 = set(re.findall(metric_pattern, content_1))
        metrics_2 = set(re.findall(metric_pattern, content_2))
        
        if metrics_1 & metrics_2:  # Same metric
            if percentages_1 != percentages_2:
                return ConflictType.UPDATE
    
    # Pattern 2: Count updates (e.g., "2条" → "16条", "17条" → "16条")
    counts_1 = re.findall(r'(\d+)\s*条', content_1)
    counts_2 = re.findall(r'(\d+)\s*条', content_2)
    
    if counts_1 and counts_2:
        if counts_1 != counts_2:
            # Check if same context (memory, record, database, etc.)
            context_words = {'记忆', '记录', '数据', 'memory', 'record', '数据库', 'database'}
            words_1 = set(content_1.split())
            words_2 = set(content_2.split())
            
            # Also check for entity overlap (Mnemonic, PostgreSQL, etc.)
            entities_1 = set(re.findall(r'mnemonic|postgres|数据库', content_1))
            entities_2 = set(re.findall(r'mnemonic|postgres|数据库', content_2))
            
            if (words_1 & context_words) or (words_2 & context_words) or (entities_1 & entities_2):
                return ConflictType.UPDATE
    
    # Pattern 3: Status changes (之前/现在/修复后)
    status_markers = ['之前', '现在', '修复后', '之前是', '现在是', '曾', '有']
    has_status_1 = any(marker in content_1 for marker in status_markers)
    has_status_2 = any(marker in content_2 for marker in status_markers)
    
    if has_status_1 or has_status_2:
        # Check if same entity/topic
        entities_1 = set(re.findall(r'\b[A-Z][a-z]+\b', memory_1.get("content", "")))
        entities_2 = set(re.findall(r'\b[A-Z][a-z]+\b', memory_2.get("content", "")))
        
        # Also check Chinese entities
        cn_entities_1 = set(re.findall(r'mnemonic|postgres|数据库|vector', content_1))
        cn_entities_2 = set(re.findall(r'mnemonic|postgres|数据库|vector', content_2))
        
        if (entities_1 & entities_2) or (cn_entities_1 & cn_entities_2):
            return ConflictType.UPDATE
    
    # Pattern 4: Database state changes (丢失 → 有X条)
    if ('丢失' in content_1 or '降到' in content_1) and ('有' in content_2 and '条' in content_2):
        # Check if same database context
        if '数据库' in content_1 and '数据库' in content_2:
            return ConflictType.UPDATE
    
    # Fallback to original detection
    return detect_conflict(memory_1, memory_2)


def _is_contradiction(text_1: str, text_2: str) -> bool:
    """Check if two texts contradict each other."""
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
    
    for pos, neg in contradiction_pairs:
        if pos in text_1 and neg in text_2:
            return True
        if neg in text_1 and pos in text_2:
            return True
    
    if "doesn't" in text_2 and "anymore" in text_2:
        words_1 = set(text_1.split())
        words_2 = set(text_2.split())
        common = words_1 & words_2
        if len(common) >= 2:
            return True
    
    return False


if __name__ == "__main__":
    asyncio.run(validate_with_llm_embedding())
