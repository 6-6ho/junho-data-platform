FROM python:3.12-slim

# System deps — psycopg2 needs libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for layer caching
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

# Copy source
COPY rag_server /app/rag_server
COPY ingest /app/ingest
COPY scripts /app/scripts

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Default healthcheck binds to /health
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["python", "-m", "rag_server.main"]
