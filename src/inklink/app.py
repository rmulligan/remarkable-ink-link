"""FastAPI application for InkLink API endpoints."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from inklink.controllers.syntax_controller import router as syntax_router
from inklink.di.service_provider import ServiceProvider

app = FastAPI(
    title="InkLink API",
    description="API for InkLink Agentic Framework",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Nuxt dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(syntax_router)

# Dependency injection setup
service_provider = ServiceProvider()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Initialize services
    await service_provider.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await service_provider.shutdown()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "InkLink API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
