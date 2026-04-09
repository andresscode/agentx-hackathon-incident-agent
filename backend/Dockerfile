FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev

COPY scripts/ scripts/
COPY app/ app/

# Clone the Reaction Commerce codebase and build the search index
RUN git clone --depth 1 https://github.com/reactioncommerce/reaction.git /tmp/reaction && \
    uv run python scripts/build_codebase_index.py /tmp/reaction /app/codebase_data && \
    rm -rf /tmp/reaction

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
