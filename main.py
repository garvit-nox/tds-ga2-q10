import time, uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

ALLOWED_ORIGINS = [
    "https://app-57xuu7.example.com",
    # Also add exam page origin if known
]
RATE_LIMIT  = 10
WINDOW_SECS = 10

rate_buckets: dict = {}

class FullMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin    = request.headers.get("origin", "")
        client_id = request.headers.get("x-client-id", "")

        # --- Rate limiting ---
        if client_id:
            now    = time.time()
            bucket = rate_buckets.setdefault(client_id, [])
            bucket[:] = [t for t in bucket if now - t < WINDOW_SECS]
            if len(bucket) >= RATE_LIMIT:
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(WINDOW_SECS)},
                    content={"detail": "Rate limit exceeded"},
                )
            bucket.append(now)

        # --- Request ID ---
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Inject into request state for route handlers
        request.state.request_id = request_id

        response = await call_next(request)

        # --- CORS headers ---
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"]  = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id"

        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(FullMiddleware)

@app.options("/ping")
async def ping_preflight(request: Request):
    origin = request.headers.get("origin", "")
    headers = {"Access-Control-Allow-Methods": "GET, OPTIONS",
               "Access-Control-Allow-Headers": "X-Request-ID, X-Client-Id"}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
    return JSONResponse(status_code=200, headers=headers, content={})

@app.get("/ping")
async def ping(request: Request):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        content={
            "email":      "24f1000625@ds.study.iitm.ac.in",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )
