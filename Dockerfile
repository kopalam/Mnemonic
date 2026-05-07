# Mnemonic API Dockerfile
# Multi-stage build for smaller image

FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies only (NOT the mnemonic package itself —
# code is mounted via volume at runtime, so we must avoid
# site-packages shadowing the mounted /app/mnemonic)
RUN uv pip install --system --no-cache \
    "fastapi>=0.110" \
    "uvicorn[standard]>=0.29" \
    "sqlalchemy[asyncio]>=2.0" \
    "asyncpg>=0.29" \
    "pgvector>=0.3" \
    "pydantic>=2.0" \
    "pyyaml>=6.0" \
    "openai>=1.20" \
    "httpx>=0.27" \
    "jieba>=0.42"

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create directory structure (code will be mounted via volume)
RUN mkdir -p /app/mnemonic

# Create non-root user
RUN useradd -m -u 1000 mnemonic && chown -R mnemonic:mnemonic /app
USER mnemonic

# Expose port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8010/health').raise_for_status()" || exit 1

# Run with uvicorn (no --reload for production)
CMD ["uvicorn", "mnemonic.api:app", "--host", "0.0.0.0", "--port", "8010", "--log-level", "info"]