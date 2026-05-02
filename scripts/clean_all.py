"""Clean all test data, keep a known-good seed set for search quality evaluation."""
import asyncio, asyncpg

async def clean():
    conn = await asyncpg.connect('postgresql://mnemonic:mnemonic_dev_password@localhost:5434/mnemonic')
    
    # Nuclear: hard-delete everything
    await conn.execute('DELETE FROM memory_access_logs')
    deleted = await conn.execute('DELETE FROM memories')
    print(f'Cleaned all memories.')
    
    # Verify empty
    count = await conn.fetchval('SELECT count(*) FROM memories')
    print(f'Remaining: {count}')
    
    await conn.close()

asyncio.run(clean())
