"""
FairMed Backend Application
Main FastAPI application entry point with modular REST API routing, CORS, and error handling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routers.auth import router as auth_router
from app.routers.bills import router as bills_router
from app.routers.ocr import router as ocr_router
from app.routers.medicines import router as medicines_router
from app.routers.audit import router as audit_router
from app.routers.reports import router as reports_router
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    init_db()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FairMed is an AI-powered medical bill auditing backend designed to verify hospital medicine bills "
        "against official Government of India (NPPA / DPCO 2013 / NLEM) ceiling prices, notified trade-margin caps, "
        "and verified MRP schedules to identify potential overcharging."
    ),
    lifespan=lifespan
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include Routers
app.include_router(auth_router)
app.include_router(bills_router)
app.include_router(ocr_router)
app.include_router(medicines_router)
app.include_router(audit_router)
app.include_router(reports_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint indicating API operational status."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
