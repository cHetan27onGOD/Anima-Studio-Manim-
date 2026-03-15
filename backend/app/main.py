from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import redis.asyncio as aioredis

from app.api.routes import router
from app.api.auth import router as auth_router
from app.core.config import settings
from app.templates.capabilities import initialize_all_capabilities

app = FastAPI(
    title="AnimaStudio API",
    description="Graph rendering service with Manim",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Redis client for rate limiting and correlation
redis_client = aioredis.from_url(settings.REDIS_URL)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/api/jobs":
        try:
            ip = request.client.host if request.client else "unknown"
            key = f"rate:{ip}"
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, 60)
            if count > 10:
                cid = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many render requests",
                        "hint": "Wait up to 60 seconds and try again",
                        "correlation_id": cid,
                    },
                )
        except Exception as e:
            print(f"Rate limit error: {e}")
    
    response = await call_next(request)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    cid = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    detail = exc.detail
    # Ensure detail is a string for consistent frontend display
    if not isinstance(detail, str):
        detail = str(detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "HTTP_ERROR",
            "message": detail,
            "detail": detail,  # Provide both for compatibility
            "correlation_id": cid,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    cid = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    error_msg = str(exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "Unexpected error",
            "detail": error_msg,
            "details": error_msg,
            "correlation_id": cid,
        },
    )


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting AnimaStudio API on {settings.API_HOST}:{settings.API_PORT}")
    print(f"CORS origins configured: {['http://localhost:3000', 'http://127.0.0.1:3000', 'http://0.0.0.0:3000']}, allow_credentials=True")
    print(f"Environment: {settings.ENVIRONMENT}")

    # Initialize template capability registry for planner routing
    try:
        initialize_all_capabilities()
        print("Template capabilities initialized successfully.")
    except Exception as e:
        print(f"Error initializing template capabilities: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("Shutting down AnimaStudio API")
