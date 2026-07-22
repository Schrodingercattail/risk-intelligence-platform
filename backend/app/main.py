"""
FastAPI Application Entry Point

This is the main application file that sets up the FastAPI app,
middleware, and includes all route modules.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db.session import engine
from app.models.database import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Debug mode: {settings.DEBUG}")

    # Create database tables (for development)
    # In production, use Alembic migrations instead
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    print("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Risk Intelligence Platform API - Machine Learning Driven Detection, Monitoring & Investigation",
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Include route modules
from app.api.routes import risk, cases, pipeline, model

app.include_router(risk.router, prefix=settings.API_PREFIX, tags=["Risk"])
app.include_router(cases.router, prefix=settings.API_PREFIX, tags=["Cases"])
app.include_router(pipeline.router, prefix=settings.API_PREFIX, tags=["Pipeline"])
app.include_router(model.router, prefix=settings.API_PREFIX, tags=["Model"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
