"""重新生成所有记忆的 content_tokens"""
import asyncio
from mnemonic.services import tokenize_for_search
from mnemonic.database import async_session
from sqlalchemy import text

async def fix_content_tokens():
    async with async_session() as session:
        # 获取所有活跃记忆
        result = await session.execute(
            text("SELECT id, content FROM memories WHERE deleted_at IS NULL")
        )
        memories = result.fetchall()
        print(f"找到 {len(memories)} 条记忆")
        
        updated = 0
        for mem_id, content in memories:
            tokens = tokenize_for_search(content)
            if tokens:
                await session.execute(
                    text("UPDATE memories SET content_tokens = to_tsvector('simple', :tokens) WHERE id = :id"),
                    {"tokens": tokens, "id": str(mem_id)}
                )
                updated += 1
                print(f"  [{updated}] {content[:50]}...")
        
        await session.commit()
        print(f"\n更新了 {updated} 条记忆的 content_tokens")
        
        # 验证 ATR
        result = await session.execute(
            text("SELECT id, content_tokens FROM memories WHERE content ILIKE '%ATR%' AND deleted_at IS NULL")
        )
        rows = result.fetchall()
        print(f"\n验证 ATR 词条:")
        for row in rows:
            has_atr = "'atr'" in str(row[1])
            print(f"  ID: {row[0][:8]}... | 包含 'atr': {has_atr}")

if __name__ == "__main__":
    asyncio.run(fix_content_tokens())
