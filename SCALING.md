# SCALING.md -- Scalability Analysis

## Current Architecture

Single Docker Compose deployment with all services on one host.

| Service | Resource Profile | Scaling Unit |
|---------|-----------------|--------------|
| Frontend (Next.js) | Low CPU, low memory | Stateless -- horizontal |
| Backend (FastAPI) | CPU-bound during LLM calls, ~50MB memory for codebase index | Stateless -- horizontal |
| PostgreSQL | I/O-bound | Vertical, then read replicas |
| Arize Phoenix | Memory for trace storage | Single instance (dev/observability) |
| Peppermint | Low resource | Single instance |

## Current Capacity

- **Throughput:** Each incident triage takes 10-20 seconds (3 sequential LLM calls + hook execution). FastAPI's async architecture handles concurrent requests -- multiple incidents triage simultaneously via `BackgroundTasks`.
- **Concurrency:** Limited by LLM provider rate limits, not by the application. A single backend instance can handle ~10-20 concurrent triage jobs before API throttling.
- **Storage:** PostgreSQL handles incident records efficiently. Image storage in `LargeBinary` columns works for low-to-moderate volume.

## Bottlenecks

### 1. Sequential LLM Calls (Primary Latency Source)

The triage pipeline makes 3 LLM calls in sequence: classify -> search -> summarize. Each takes 2-5 seconds.

**Mitigation:**
- **Parallelize:** Classify and search nodes could run concurrently -- search only needs keywords (available after classify). LangGraph supports parallel edges.
- **Faster models:** Use lighter models for classification (Gemini Flash Lite) while keeping stronger models for summary generation.
- **Cache classifications:** Incidents with similar descriptions could reuse cached results.

### 2. Background Task Processing

FastAPI `BackgroundTasks` runs triage in the same process. No retry, no job visibility, no distribution.

**Mitigation:**
- **Message queue:** Redis/RabbitMQ + Celery or ARQ workers.
  - Dedicated worker pools (scale independently from API)
  - Retry with exponential backoff
  - Job status tracking and dead-letter queues
  - Per-provider rate limiting

### 3. Image Storage

Images stored as `LargeBinary` in PostgreSQL increase row size and slow queries.

**Mitigation:**
- **Object storage:** S3/MinIO for images, store only URLs in PostgreSQL.
- **Image processing:** Resize/compress before storage -- LLM only needs ~1080p to read error messages.

### 4. Codebase Index

The Reaction Commerce index is loaded in memory per worker (~50MB). Each worker holds its own copy.

**Mitigation:**
- **Shared index service:** Redis cache or dedicated microservice.
- **Vector search:** Replace keyword matching with embeddings (pgvector, Pinecone) for better relevance.

## Scaling Phases

### Phase 1: Moderate Load (10-100 incidents/hour)

- Load balancer in front of multiple backend instances
- Managed PostgreSQL with connection pooling
- LLM provider rate limit configuration + client-side throttling

### Phase 2: High Load (100-1000 incidents/hour)

- Message queue (Redis + ARQ or Celery) replacing `BackgroundTasks`
- Dedicated triage worker pools (scale based on queue depth)
- Images moved to object storage (S3/MinIO)
- Redis caching for codebase search results and repeated classifications
- Per-provider LLM routing to distribute load

### Phase 3: Production Scale (1000+ incidents/hour)

- Kubernetes with horizontal pod autoscaling
- Vector search for codebase analysis (pgvector or dedicated vector DB)
- Streaming triage results via WebSockets (show classification before summary completes)
- Multi-region deployment
- Production observability stack (Grafana + Prometheus replacing Phoenix)

## Cost Considerations

| Component | Cost Driver | Optimization |
|-----------|------------|--------------|
| LLM API calls | 3-4 calls per incident (~2K-5K tokens each) | Cheaper models for classification, cache repeated patterns |
| PostgreSQL | Storage growth from image blobs | Move to object storage |
| Infrastructure | Compute for workers | Auto-scale on queue depth, scale to zero off-hours |

At current usage (GPT-4o-mini via OpenRouter), estimated cost per triage: ~$0.002-0.005. At 1000 incidents/day, LLM costs: ~$2-5/day.

## Monitoring for Scale

Metrics to track for scaling decisions:

- **Triage latency** (p50, p95, p99) -- per node and end-to-end
- **Queue depth** -- pending triage jobs (once queue is implemented)
- **LLM error rate** -- per provider, to trigger failover
- **Token usage** -- per model, per node, for cost tracking
- **Concurrent triage jobs** -- to size worker pools
- **Database connection pool utilization** -- to size PostgreSQL

## Key Technical Decisions

| Decision | Trade-off | Rationale |
|----------|----------|-----------|
| FastAPI `BackgroundTasks` over message queue | No retry/distribution, but zero operational overhead | Sufficient for hackathon scope; queue is the first production upgrade |
| Pre-built codebase index over runtime search | Static (no live updates), but fast and deterministic | Reaction Commerce repo doesn't change; index baked into Docker image |
| PostgreSQL image storage over S3 | Doesn't scale, but simpler deployment | Single `docker compose up` for evaluators; production would use S3 |
| Multi-provider LLM abstraction | Added complexity, but enables failover and cost optimization | Already paid off during development (switched providers multiple times) |
