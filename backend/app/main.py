"""KAILASA ERP — FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from uuid import uuid4
import logging

from app.config import settings
from app.database import async_engine, AsyncSessionLocal
from app.services.audit_service import AuditEvent, AuditEventCategory, TripleAuditWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton audit writer (used by middleware, system events, and the auth module)
_audit_writer: TripleAuditWriter | None = None


def get_audit_writer() -> TripleAuditWriter:
    global _audit_writer
    if _audit_writer is None:
        _audit_writer = TripleAuditWriter(
            base_path=settings.AUDIT_STORAGE_PATH,
            system_name="erp",
        )
    return _audit_writer


def _system_event(action: str, details: dict | None = None) -> None:
    """Fire a SYSTEM-category audit event (non-blocking)."""
    get_audit_writer().fire_and_forget(AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        category=AuditEventCategory.SYSTEM,
        user_id=None,
        username="system",
        action=action,
        resource_type="system",
        resource_id=None,
        details=details,
        ip_address=None,
        system_name="erp",
    ))


scheduler = AsyncIOScheduler()


async def run_audit_retention_purge():
    """Purge expired audit events from all three stores."""
    from app.services.audit_retention import purge_audit_retention

    _system_event("system.scheduler.audit_retention_purge", {"status": "started"})
    try:
        summary = await purge_audit_retention(
            settings.AUDIT_STORAGE_PATH,
            AsyncSessionLocal,
        )
        logger.info(f"Audit retention purge: {summary}")
        _system_event("system.scheduler.audit_retention_purge", {
            "status": "completed", **summary,
        })
    except Exception as e:
        logger.error(f"Audit retention purge failed: {e}")
        _system_event("system.scheduler.audit_retention_purge", {
            "status": "failed", "error": str(e),
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting KAILASA ERP API...")
    _system_event("system.startup")

    # Verify DB connection
    try:
        async with async_engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 1")
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # Schedule jobs
    scheduler.add_job(run_audit_retention_purge, "interval", hours=24, id="audit_retention_purge")
    scheduler.start()
    logger.info("Scheduled jobs started (audit retention)")

    logger.info("KAILASA ERP API started successfully")
    yield

    # Shutdown
    _system_event("system.shutdown")
    scheduler.shutdown()
    await async_engine.dispose()
    logger.info("KAILASA ERP API shut down")


app = FastAPI(
    title="KAILASA ERP",
    description="Non-profit ERP system for KAILASA — General Ledger, Fund Accounting, and Subsystem Integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Read-access audit middleware for sensitive endpoints
from app.middleware.audit_middleware import AuditReadAccessMiddleware

ERP_SENSITIVE_PREFIXES = [
    "/api/reports/",
    "/api/dashboard",
    "/api/gl/trial-balance",
    "/api/admin/audit-log",
    "/api/admin/users",
]
app.add_middleware(
    AuditReadAccessMiddleware,
    writer=get_audit_writer(),
    prefixes=ERP_SENSITIVE_PREFIXES,
    system_name="erp",
)

# Import and register routers
from app.routes import admin, auth, gl, reports, org, contacts, subsystems, dashboard

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(gl.router)
app.include_router(reports.router)
app.include_router(org.router)
app.include_router(contacts.router)
app.include_router(subsystems.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "KAILASA ERP API", "version": "1.0.0"}
