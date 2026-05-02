"""Inventory all memories in DB."""
import asyncio, asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://mnemonic:mnemonic_dev_password@localhost:5434/mnemonic')
    rows = await conn.fetch('''
        SELECT id, client_id, user_id, agent_id, session_id, content, memory_type, importance, deleted_at IS NOT NULL as is_deleted
        FROM memories ORDER BY created_at ASC
    ''')
    print(f'Total records: {len(rows)}')
    print()
    ns_map = {}
    for row in rows:
        ns = f"{row['client_id']}:{row['user_id']}:{row['agent_id']}:{row['session_id'] or 'NULL'}"
        if ns not in ns_map:
            ns_map[ns] = []
        ns_map[ns].append(row)
    
    for ns, items in ns_map.items():
        active = [i for i in items if not i['is_deleted']]
        deleted = [i for i in items if i['is_deleted']]
        print(f'--- {ns} ---')
        print(f'  active={len(active)}, deleted={len(deleted)}')
        for i in active:
            print(f'  [{str(i["id"])[:8]}] {i["memory_type"]:12s} imp={i["importance"]:.2f} | {i["content"][:60]}')
    await conn.close()

asyncio.run(check())
