# Mnemonic Memory Plugin

Self-hosted memory system for Hermes Agent.

## Features

- **BM25 Keyword Search** — Fast, precise term matching
- **Vector Search** — Semantic similarity search
- **Auto Deduplication** — LLM-based 3-phase deduplication (ADD/UPDATE/DELETE/NONE)
- **Memory Merging** — Fragments merged into complete semantic statements
- **Circuit Breaker** — Auto-disable on consecutive failures

## Configuration

### Environment Variables

```bash
MNEMONIC_API_URL=http://localhost:8010
MNEMONIC_NAMESPACE=hermes:boss:hnoe:*
```

### Config File

Create `$HERMES_HOME/mnemonic.json`:

```json
{
  "api_url": "http://localhost:8010",
  "namespace": "hermes:boss:hnoe:*"
}
```

## Activation

Add to `$HERMES_HOME/config.yaml`:

```yaml
memory:
  provider: mnemonic
```

## Tools

### mnemonic_search

Search memories by keyword or semantic meaning.

```json
{
  "query": "ATR 止损",
  "mode": "keyword",
  "limit": 5
}
```

### mnemonic_extract

Extract and store facts from text.

```json
{
  "text": "用户要求将 SOL 止损改为 3x ATR"
}
```

## Architecture

```
Hermes Agent
    ↓
MemoryProvider interface
    ↓
MnemonicMemoryProvider (this plugin)
    ↓
HTTP API (localhost:8010)
    ↓
Mnemonic Backend (FastAPI + PostgreSQL + pgvector)
```

## Fallback

If Mnemonic API is unreachable, the plugin returns empty results.
Built-in memory (MEMORY.md / USER.md) remains active as fallback.
