"""Validation using real LLM extraction from Mnemonic services."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv
load_dotenv(Path("/Users/kopa/Documents/monic/.env"))

from mnemonic.services import ExtractionService
from mnemonic.conflict_detection import detect_conflict, ConflictType, Conflict
from mnemonic.temporal_decay import calculate_temporal_importance
from mnemonic.adaptive_window import determine_extraction_window

from validation.real_dataset import REAL_CONVERSATIONS, REAL_SEARCH_QUERIES, DATASET_STATS


async def validate_with_llm():
    """Run validation using real LLM extraction."""
    print("=" * 60)
    print("Mnemonic Validation - Real LLM Extraction")
    print("=" * 60)
    print(f"\nDataset Statistics:")
    print(f"  Total Conversations: {DATASET_STATS['total_conversations']}")
    print(f"  Source Sessions: {len(DATASET_STATS['source_sessions'])}")
    
    extraction_service = ExtractionService()
    
    # D1: Extraction Quality with LLM
    print("\n" + "=" * 60)
    print("[D1] Extraction Quality (LLM)")
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
            
            # Match with expected (semantic similarity)
            for exp_mem in conv["expected_memories"]:
                exp_content = exp_mem["content"].lower()
                for ext_mem in extracted:
                    ext_content = ext_mem.get("content", "").lower()
                    
                    # Check keyword overlap
                    exp_words = set(exp_content.split())
                    ext_words = set(ext_content.split())
                    overlap = exp_words & ext_words
                    
                    # More lenient: 20% overlap OR key entities match
                    overlap_ratio = len(overlap) / min(len(exp_words), len(ext_words)) if min(len(exp_words), len(ext_words)) > 0 else 0
                    
                    # Check for key entity matches (numbers, proper nouns)
                    import re
                    exp_entities = set(re.findall(r'\b[A-Z][a-z]+\b|\d+%?', exp_mem["content"]))
                    ext_entities = set(re.findall(r'\b[A-Z][a-z]+\b|\d+%?', ext_mem.get("content", "")))
                    entity_overlap = exp_entities & ext_entities
                    
                    if overlap_ratio >= 0.2 or len(entity_overlap) >= 2:
                        correct_matches += 1
                        print(f"  ✓ Matched: {ext_content[:60]}...")
                        break
            
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
    
    # D2: Conflict Detection
    print("\n" + "=" * 60)
    print("[D2] Conflict Resolution")
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
        
        conflict_type = detect_conflict(old_mem, expected)
        
        if conflict_type in [ConflictType.UPDATE, ConflictType.CONTRADICTION]:
            correct_conflicts += 1
            print(f"\n  {conv['id']}: ✓ {conflict_type.name}")
        else:
            print(f"\n  {conv['id']}: ✗ Expected UPDATE/CONTRADICTION, got {conflict_type.name}")
    
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
                print(f"\n  {conv['id']}: ✓ Filtered (0 memories extracted)")
            else:
                print(f"\n  {conv['id']}: ✗ Not filtered ({len(extracted)} memories extracted)")
        except Exception as e:
            print(f"\n  {conv['id']}: Error - {e}")
    
    noise_rate = 1 - (filtered / total_noise) if total_noise > 0 else 0.0
    
    print(f"\n  Total Noise: {total_noise}")
    print(f"  Filtered: {filtered}")
    print(f"  Noise Rate: {noise_rate:.2%}")
    print(f"  Target: ≤ 10%")
    print(f"  Status: {'PASS ✓' if noise_rate <= 0.10 else 'FAIL ✗'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY (LLM Extraction)")
    print("=" * 60)
    print(f"D1 Extraction F1: {f1:.2%} {'✓' if f1 >= 0.75 else '✗'}")
    print(f"D2 Conflict Accuracy: {conflict_accuracy:.2%} {'✓' if conflict_accuracy >= 0.90 else '✗'}")
    print(f"D3 Noise Rate: {noise_rate:.2%} {'✓' if noise_rate <= 0.10 else '✗'}")
    
    overall_pass = f1 >= 0.75 and conflict_accuracy >= 0.90 and noise_rate <= 0.10
    
    print("=" * 60)
    print(f"Overall: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "method": "llm_extraction",
        "d1_extraction": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "total_expected": total_expected,
            "total_extracted": total_extracted,
            "correct_matches": correct_matches,
        },
        "d2_conflict_resolution": {
            "total": total_conflicts,
            "correct": correct_conflicts,
            "accuracy": conflict_accuracy,
        },
        "d3_robustness": {
            "total": total_noise,
            "filtered": filtered,
            "noise_rate": noise_rate,
        },
        "extraction_details": extraction_results,
        "overall_pass": overall_pass,
    }
    
    report_path = Path("/Users/kopa/Documents/monic/validation/llm_extraction_report.json")
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")
    
    return report


async def main():
    await validate_with_llm()


if __name__ == "__main__":
    asyncio.run(main())