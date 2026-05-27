# ── Base image ───────────────────────────────────────────────
FROM python:3.11-slim

# ── System dependencies for psycopg2 ─────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project files ────────────────────────────────────────
COPY pipeline/ ./pipeline/
COPY scripts/  ./scripts/
COPY sql/      ./sql/
COPY data/     ./data/

# ── Python path ───────────────────────────────────────────────
ENV PYTHONPATH=/app

# ── Default command ───────────────────────────────────────────
# Run the full pipeline. Override with:
#   docker compose run pipeline python scripts/generate_data.py
CMD ["python", "pipeline/runner.py"]