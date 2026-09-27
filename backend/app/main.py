from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.errors import register_error_handlers

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-assisted Digital Examination & On-Screen Marking Platform",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register application error handlers
register_error_handlers(app)

# Mount API v1 router
from app.api.v1 import api_v1_router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


def _check_db_status() -> str:
    """
    Helper to verify database connectivity with SELECT 1.
    Uses a 5-second connect_timeout so the health check never hangs indefinitely.
    """
    try:
        # Create a short-lived engine with a connection timeout for the probe
        probe_engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=False,
            connect_args={"connect_timeout": 5},
        )
        with probe_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe_engine.dispose()
        return "connected"
    except Exception as exc:
        return f"unavailable ({type(exc).__name__})"


@app.get("/health", tags=["Health"], summary="System health check")
def health_check():
    """
    Health check endpoint returning service status and database connectivity.
    Always returns HTTP 200 for liveness monitoring.
    """
    db_status = _check_db_status()
    return {
        "status": "ok",
        "database": db_status,
    }


@app.get(f"{settings.API_V1_STR}/health", tags=["Health"], summary="API v1 health check")
def api_v1_health_check():
    """
    Convenience alias for /health under the api/v1 namespace.
    """
    return health_check()
