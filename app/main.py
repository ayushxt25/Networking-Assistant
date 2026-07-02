"""
Application Entry Point
-------------------------
Creates the FastAPI app, initializes the database (creating tables on
startup if they don't exist), registers the auth and conversation routers,
wires up the slowapi rate limiter (using its standard exception handler),
and exposes a health-check endpoint.

New feature areas can be added as separate router files and included here
without touching existing code -- a hub-and-spoke routing architecture.
"""

import contextvars
import logging
from uuid import uuid4

from dotenv import load_dotenv

# Must run before importing anything that reads environment variables at
# module level (app.auth reads SECRET_KEY, app.database reads DATABASE_URL).
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.database import init_db
from app.rate_limit import limiter
from app.routes.analytics import router as analytics_router
from app.routes.audit import router as audit_router
from app.routes.auth import router as auth_router
from app.routes.conversation import router as conversation_router
from app.routes.network import router as network_router
from app.routes.opportunities import router as opportunities_router
from app.routes.personalization import router as personalization_router
from app.routes.recommendations import router as recommendations_router
from app.routes.retrieval import router as retrieval_router
from app.routes.relationship_data import router as relationship_data_router
from app.routes.relationship_scores import router as relationship_scores_router
from app.services.health_service import get_dependency_health

correlation_id_var = contextvars.ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | corr=%(correlation_id)s | %(message)s",
)
logger = logging.getLogger("networking_assistant")
for handler in logging.getLogger().handlers:
    handler.addFilter(CorrelationIdFilter())

app = FastAPI(
    title="Personalized Networking Assistant API",
    description=(
        "AI-powered backend that extracts themes from event descriptions, "
        "generates conversation starters, fact-checks topics via Wikipedia, "
        "and logs per-user conversation history and feedback."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _error_code_for_status(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
    }.get(status_code, "http_error")


def _error_response(
    request: Request,
    status_code: int,
    message: str,
    *,
    details=None,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", correlation_id_var.get())
    payload = {
        "error": {
            "code": _error_code_for_status(status_code),
            "message": message,
            "details": details,
        },
        "detail": details if details is not None else message,
        "correlation_id": correlation_id,
    }
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers={"X-Correlation-ID": correlation_id},
    )


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
    token = correlation_id_var.set(correlation_id)
    request.state.correlation_id = correlation_id
    try:
        response = await call_next(request)
    except Exception:
        correlation_id_var.reset(token)
        raise
    response.headers["X-Correlation-ID"] = correlation_id
    correlation_id_var.reset(token)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _error_response(request, exc.status_code, message, details=exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Request validation failed",
        details=exc.errors(),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("Rate limit exceeded")
    return _error_response(
        request,
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Rate limit exceeded",
        details={"limit": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request failure")
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal server error",
    )


# Required for the @limiter.limit(...) decorators in app/routes/conversation.py
# to function: slowapi looks up the limiter via request.app.state.limiter.
app.state.limiter = limiter


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialized and application startup complete.")


app.include_router(auth_router)
app.include_router(conversation_router)
app.include_router(relationship_data_router)
app.include_router(relationship_scores_router)
app.include_router(opportunities_router)
app.include_router(personalization_router)
app.include_router(recommendations_router)
app.include_router(retrieval_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(network_router)


@app.get("/")
def health_check() -> dict:
    dependency_health = get_dependency_health()
    return {
        "status": "ok",
        "service": "Personalized Networking Assistant API",
        "dependencies": dependency_health["dependencies"],
    }


@app.get("/health")
def health() -> dict:
    dependency_health = get_dependency_health()
    return {"status": dependency_health["status"], "dependencies": dependency_health["dependencies"]}


@app.get("/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    dependency_health = get_dependency_health()
    return dependency_health
