"""KAILASA ERP — FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting KAILASA ERP API...")

    # Verify DB connection
    try:
        async with async_engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 1")
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    logger.info("KAILASA ERP API started successfully")
    yield

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

# Import and register routers
from app.routes import auth, gl, reports, org, contacts, subsystems, dashboard

app.include_router(auth.router)
app.include_router(gl.router)
app.include_router(reports.router)
app.include_router(org.router)
app.include_router(contacts.router)
app.include_router(subsystems.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "KAILASA ERP API", "version": "1.0.0"}
