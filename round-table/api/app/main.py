# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Round Table API - Main Application"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .websocket.routes import on_websocket_startup, on_websocket_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    # Startup
    print(f"🏰 Round Table API v{settings.app_version} starting...")
    print(f"📊 Debug mode: {settings.debug}")

    # Initialize WebSocket and Message Bus
    try:
        await on_websocket_startup()
        print("📡 Message bus initialized")
    except Exception as e:
        print(f"⚠️  Warning: Message bus initialization failed: {e}")
        print("   WebSocket features will be unavailable until Redis is connected")

    yield

    # Shutdown
    print("👋 Round Table API shutting down...")
    await on_websocket_shutdown()
    print("📡 Message bus shut down")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Agent Collaboration Bus",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket routes
from .websocket.routes import websocket_router
app.include_router(websocket_router)

# Include auth routes
from .auth.routes import router as auth_router
app.include_router(auth_router, prefix=settings.api_prefix)

# Include API routes
from .api import (
    workspaces_router,
    sandboxes_router,
    messages_router,
    collaborations_router,
    system_router,
)
app.include_router(workspaces_router, prefix=settings.api_prefix)
app.include_router(sandboxes_router, prefix=settings.api_prefix)
app.include_router(messages_router, prefix=settings.api_prefix)
app.include_router(collaborations_router, prefix=settings.api_prefix)
app.include_router(system_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version
    }


@app.get(settings.api_prefix)
async def api_root():
    """API root endpoint"""
    return {
        "message": "Round Table API",
        "version": settings.app_version,
        "docs": "/docs"
    }
