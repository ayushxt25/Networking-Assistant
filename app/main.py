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

import logging

from dotenv import load_dotenv

# Must run before importing anything that reads environment variables at
# module level (app.auth reads SECRET_KEY, app.database reads DATABASE_URL).
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import init_db
from app.rate_limit import limiter
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router
from app.routes.conversation import router as conversation_router
from app.routes.recommendations import router as recommendations_router
from app.routes.relationship_data import router as relationship_data_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("networking_assistant")

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

# Required for the @limiter.limit(...) decorators in app/routes/conversation.py
# to function: slowapi looks up the limiter via request.app.state.limiter.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialized and application startup complete.")


app.include_router(auth_router)
app.include_router(conversation_router)
app.include_router(relationship_data_router)
app.include_router(recommendations_router)
app.include_router(analytics_router)


@app.get("/")
def health_check() -> dict:
    """Simple health-check endpoint used to verify the API is up and reachable."""
    return {"status": "ok", "service": "Personalized Networking Assistant API"}
