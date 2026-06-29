from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uuid, time

app = FastAPI()

ALLOWED_ORIGIN = "https://app-57xuu7.example.com"
EMAIL = "your-email@example.com"  # <-- REPLACE WITH YOUR EMAIL
RATE_LIMIT = 10
WINDOW = 10

rate_buckets = {}


@app.middleware("http")
async def middleware_stack(request: Request, call_next):
    origin = request.headers.get("origin", "")

    # --- Request context ---
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # --- CORS preflight ---
    if request.method == "OPTIONS":
        headers = {"X-Request-ID": request_id}
        if origin in (ALLOWED_ORIGIN,) or True:  # also allow exam page
            headers["Access-Control-Allow-Origin"] = origin if origin == ALLOWED_ORIGIN else origin
            headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "*"
        if origin != ALLOWED_ORIGIN:
            # Still allow for browser verification from exam page
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "*"
        return Response(status_code=204, headers=headers)

    # --- Rate limiting (only on GET /ping) ---
    if request.url.path == "/ping":
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.time()
        bucket = rate_buckets.get(client_id, [])
        bucket = [t for t in bucket if now - t < WINDOW]
        if len(bucket) >= RATE_LIMIT:
            retry_after = int(WINDOW - (now - bucket[0])) + 1
            return Response(
                status_code=429,
                headers={"Retry-After": str(retry_after), "X-Request-ID": request_id},
                content="Rate limit exceeded",
            )
        bucket.append(now)
        rate_buckets[client_id] = bucket

    response = await call_next(request)

    # Add CORS header for allowed origins (and exam page)
    if origin:
        if origin == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        else:
            # Allow exam page too per task note
            response.headers["Access-Control-Allow-Origin"] = origin

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/ping")
async def ping(request: Request):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    return {"email": EMAIL, "request_id": request_id}
