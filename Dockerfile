# Mnemonic API Dockerfile
# Multi-stage build for smaller image

FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system --no-cache .

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

# Run with uvicorn --reload for hot reload when code changes
CMD ["uvicorn", "mnemonic.api:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]