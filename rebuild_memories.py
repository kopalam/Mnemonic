#!/usr/bin/env python3
"""Rebuild boss memories: extract clean facts from raw conversation fragments."""
import asyncio
import json
import sys
import time
import httpx

API_BASE = "http://localhost:8010"
NAMESPACE = "hermes:boss:hnoe:rebuild"
OLD_NAMESPACE = "hermes:boss:hnoe:*"
BATCH_SIZE = 5
CONCURRENCY = 3  # parallel extract requests


async def fetch_all_memories(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all existing boss memories."""
    all_memories = []
    offset = 0
    while True:
        resp = await client.get(
            f"{API_BASE}/memories",
            params={"limit": 50, "offset": offset},
            headers={"x-namespace": OLD_NAMESPACE},
        )
        data = resp.json()
        all_memories.extend(data["memories"])
        if len(all_memories) >= data["total"]:
            break
        offset += 50
    return all_memories


async def extract_batch(client: httpx.AsyncClient, batch_text: str, batch_idx: int) -> dict:
    """Extract memories from a batch of text."""
    try:
        resp = await client.post(
            f"{API_BASE}/memories/extract",
            json={"conversation": batch_text},
            headers={"x-namespace": NAMESPACE, "Content-Type": "application/json"},
            timeout=120.0,
        )
        if resp.status_code == 201:
            extracted = resp.json()
            return {"batch": batch_idx, "count": len(extracted), "status": "ok"}
        else:
            return {"batch": batch_idx, "count": 0, "status": f"error_{resp.status_code}", "detail": resp.text[:200]}
    except Exception as e:
        return {"batch": batch_idx, "count": 0, "status": "exception", "detail": str(e)[:200]}


async def delete_old_memories(client: httpx.AsyncClient, memories: list[dict]):
    """Delete all old memories (session_import)."""
    deleted = 0
    for m in memories:
        if m.get("session_id") == "session_import":
            # Build exact namespace for this memory
            ns = f"{m['client_id']}:{m['user_id']}:{m['agent_id']}:{m['session_id']}"
            try:
                resp = await client.delete(
                    f"{API_BASE}/memories/{m['id']}",
                    headers={"x-namespace": ns},
                )
                if resp.status_code == 200:
                    deleted += 1
            except:
                pass
    return deleted


async def main():
    async with httpx.AsyncClient() as client:
        # Step 1: Fetch all old memories
        print("Step 1: Fetching old memories...")
        old_memories = await fetch_all_memories(client)
        print(f"  Found {len(old_memories)} old memories")
        
        # Filter only session_import ones (the raw ones)
        raw_memories = [m for m in old_memories if m.get("session_id") == "session_import"]
        print(f"  Raw (session_import) memories: {len(raw_memories)}")
        
        # Step 2: Check what's already been rebuilt
        try:
            resp = await client.get(
                f"{API_BASE}/memories",
                params={"limit": 500, "offset": 0},
                headers={"x-namespace": NAMESPACE},
            )
            resp_data = resp.json()
            already_rebuilt = resp_data.get("total", 0)
        except Exception as e:
            print(f"  Warning: Could not check rebuilt count: {e}")
            already_rebuilt = 0
        print(f"  Already rebuilt: {already_rebuilt}")
        
        if already_rebuilt > 0 and "--force" not in sys.argv:
            print("  Skipping rebuild (already done). Use --force to override.")
            print(f"\n  Total rebuilt memories: {already_rebuilt}")
            return
        
        # Step 3: Create batches
        batches = []
        for i in range(0, len(raw_memories), BATCH_SIZE):
            batch = raw_memories[i:i+BATCH_SIZE]
            conv_text = "\n".join(f"- {m['content']}" for m in batch)
            batches.append((i // BATCH_SIZE, conv_text))
        print(f"\nStep 2: Created {len(batches)} batches")
        
        # Step 4: Process batches with concurrency
        print(f"Step 3: Extracting with concurrency={CONCURRENCY}...")
        start_time = time.time()
        results = []
        total_extracted = 0
        
        semaphore = asyncio.Semaphore(CONCURRENCY)
        
        async def process_batch(idx, text):
            nonlocal total_extracted
            async with semaphore:
                result = await extract_batch(client, text, idx)
                if result["status"] == "ok":
                    total_extracted += result["count"]
                elapsed = time.time() - start_time
                print(f"  Batch {idx+1}/{len(batches)}: {result['count']} memories ({elapsed:.1f}s)")
                return result
        
        tasks = [process_batch(idx, text) for idx, text in batches]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        errors = [r for r in results if r["status"] != "ok"]
        
        print(f"\n=== Extraction Complete ===")
        print(f"Total time: {total_time:.1f}s")
        print(f"Total extracted: {total_extracted}")
        print(f"Errors: {len(errors)}")
        
        # Step 5: Delete old memories if extraction succeeded
        if total_extracted > 0 and len(errors) < len(batches) // 2:
            print(f"\nStep 4: Deleting {len(raw_memories)} old raw memories...")
            deleted = await delete_old_memories(client, raw_memories)
            print(f"  Deleted: {deleted}")
        
        # Final count
        resp = await client.get(
            f"{API_BASE}/memories",
            params={"limit": 1, "offset": 0},
            headers={"x-namespace": "hermes:boss:hnoe:*"},
        )
        print(f"\nFinal memory count: {resp.json()['total']}")


if __name__ == "__main__":
    asyncio.run(main())
