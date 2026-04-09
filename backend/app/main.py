from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import Base, engine
from .exceptions import ServiceError
from .routes import health, incidents, notifications, webhooks

# ─── OpenTelemetry / Phoenix ──────────────────────────────────────────────────
from .config import settings

if settings.PHOENIX_COLLECTOR_ENDPOINT:
    from phoenix.otel import register
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    import logging

    register(endpoint=f"{settings.PHOENIX_COLLECTOR_ENDPOINT}/v1/traces", verbose=False)

    # Instrument HTTPX and LangChain (don't need app instance)
    HTTPXClientInstrumentor().instrument()
    LangChainInstrumentor().instrument()

    logging.getLogger(__name__).info("OpenTelemetry connected to Phoenix at %s", settings.PHOENIX_COLLECTOR_ENDPOINT)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Instrument FastAPI + SQLAlchemy after app + engine exist
    if settings.PHOENIX_COLLECTOR_ENDPOINT:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    yield
    await engine.dispose()


app = FastAPI(title="Incident Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message},
    )


app.include_router(health.router)
app.include_router(incidents.router)
app.include_router(notifications.router)
app.include_router(webhooks.router)
