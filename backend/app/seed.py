"""Seed the incidents table with demo data.

Idempotent: skips if seed incidents (email = seed@nameless.dev) already exist.
Called automatically from the app lifespan on startup.
"""

import logging
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from .database import Base, async_session, engine
from .models import (
    Incident,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
)

logger = logging.getLogger("uvicorn.error")

SEED_COUNT = 45

SEED_EMAIL = "seed@nameless.dev"

TEAMS = [
    "Platform Engineering",
    "Security Response",
    "Database Team",
    "Frontend Team",
    "SRE / Infrastructure",
    "API Team",
]

DESCRIPTIONS = [
    "Checkout flow returning 500 errors for guest users",
    "Payment gateway timeout during peak hours",
    "Product search returning stale results after catalog update",
    "User sessions expiring prematurely on mobile",
    "Order confirmation emails not being delivered",
    "Inventory count mismatch between API and admin panel",
    "GraphQL query performance degradation on product listings",
    "SSL certificate expiring on CDN endpoint",
    "Database connection pool exhaustion under load",
    "Cart items disappearing after page refresh",
    "Rate limiter blocking legitimate API requests",
    "Image upload failing for files over 2MB",
    "Webhook delivery to fulfillment service failing silently",
    "Admin dashboard loading slowly due to unoptimized queries",
    "CORS errors on storefront after CDN migration",
    "Memory leak in background job worker process",
    "Shipping calculator returning incorrect rates",
    "Login page unresponsive during auth provider outage",
    "Data export job crashing on large result sets",
    "Caching layer returning stale product prices",
    "API response times spiking above 5s on /orders endpoint",
    "Elasticsearch cluster yellow status after node restart",
    "Discount code validation failing for multi-currency orders",
    "File storage quota exceeded causing upload failures",
    "Customer CSV import silently dropping rows with unicode",
    "Notification service queue backlog growing unbounded",
    "Storefront 404 errors after URL rewrite deployment",
    "Tax calculation service returning zero for international orders",
    "Background sync job stuck in retry loop",
    "Health check endpoint flapping between healthy and unhealthy",
    "Password reset tokens not expiring after use",
    "Product variant selection not updating price display",
    "Audit log missing entries for bulk operations",
    "Container OOM kills during peak traffic",
    "DNS resolution failures for internal service mesh",
    "Batch email send job timing out after 30 minutes",
    "GraphQL subscription connections dropping intermittently",
    "Stripe webhook signature verification failing",
    "Redis cluster failover causing brief cart data loss",
    "Load balancer health checks causing false-positive alarms",
    "Deployment rollback failing due to database migration lock",
    "Log ingestion pipeline dropping events under high volume",
    "API key rotation script not updating all dependent services",
    "S3 bucket policy change blocking storefront image loading",
    "Kubernetes pod autoscaler not scaling down after traffic drop",
]

# Distribution weights for realistic-looking data
STATUS_WEIGHTS = {
    IncidentStatus.PENDING: 8,
    IncidentStatus.TRIAGING: 5,
    IncidentStatus.TRIAGED: 22,
    IncidentStatus.RESOLVED: 10,
}

PRIORITY_WEIGHTS = {
    IncidentPriority.CRITICAL: 5,
    IncidentPriority.HIGH: 12,
    IncidentPriority.MEDIUM: 18,
    IncidentPriority.LOW: 10,
}

CATEGORY_WEIGHTS = {
    IncidentCategory.BUG: 8,
    IncidentCategory.SECURITY: 6,
    IncidentCategory.OUTAGE: 8,
    IncidentCategory.PERFORMANCE: 10,
    IncidentCategory.DATA_ISSUE: 7,
    IncidentCategory.OTHER: 6,
}


def _weighted_choice[T](weights: dict[T, int]) -> T:
    items = list(weights.keys())
    w = list(weights.values())
    return random.choices(items, weights=w, k=1)[0]


def _build_incidents(count: int = SEED_COUNT) -> list[Incident]:
    now = datetime.now(tz=UTC)
    incidents: list[Incident] = []

    for i in range(count):
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        created = now - timedelta(days=days_ago, hours=hours_ago)

        status = _weighted_choice(STATUS_WEIGHTS)
        # Only triaged/resolved incidents have full triage data
        has_triage = status in (IncidentStatus.TRIAGED, IncidentStatus.RESOLVED)

        incidents.append(
            Incident(
                id=uuid.uuid4(),
                name=f"Seed User {i + 1}",
                email=SEED_EMAIL,
                description=DESCRIPTIONS[i % len(DESCRIPTIONS)],
                status=status,
                priority=_weighted_choice(PRIORITY_WEIGHTS) if has_triage else None,
                category=_weighted_choice(CATEGORY_WEIGHTS) if has_triage else None,
                severity_score=random.randint(1, 10) if has_triage else None,
                assigned_team=random.choice(TEAMS) if has_triage else None,
                triage_summary=(
                    "Seed incident - triage summary placeholder."
                    if has_triage
                    else None
                ),
                created_at=created,
                updated_at=created + timedelta(minutes=random.randint(5, 120)),
            )
        )

    return incidents


async def seed() -> None:
    """Seed the database with demo incidents. Idempotent."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        count = (
            await session.execute(
                select(func.count(Incident.id)).where(Incident.email == SEED_EMAIL)
            )
        ).scalar()

        if count and count >= SEED_COUNT:
            logger.info("Database already has %d seed incidents. Skipping.", count)
            return

        incidents = _build_incidents()
        session.add_all(incidents)
        await session.commit()
        logger.info("Seeded %d incidents.", len(incidents))


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
