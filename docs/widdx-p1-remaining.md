# WIDDX Nexus — P1 Remaining Issues

> Sprint: Post-commit 9dec166  
> Date: 2026-06-26  
> Status: 4 open issues — all P1, fix before any public release

---

## Context

After closing all P0/P1 gaps in the previous sprint (auth bypass, default
permission, CodeRunner wiring, repo_mapper injection, guard wiring, DB
migrations, graceful shutdown), 4 issues from the original register remain
open. All 4 are deployment-facing — they do not affect local development but
become attack surfaces the moment the server is exposed externally.

---

## ISS-004 — No Request Size Limit

**File:** `scripts/api_server.py`  
**Severity:** P1  
**Risk:** Memory exhaustion DoS — a single large POST body can spike RAM and
freeze the server.

### The Problem

The `/api/chat` endpoint (and all other POST endpoints) accepts request bodies
of arbitrary size. There is no `Content-Length` guard or body size cap anywhere
in the FastAPI application.

```python
# Current — no guard
@app.post("/api/chat")
async def chat(req: ChatRequest):
    ...  # req.message could be 500MB
```

### The Fix

Add a middleware-level body size limit so it applies to every endpoint at once:

```python
# scripts/api_server.py — add after app = FastAPI(...)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB

class LimitBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return Response(
                content='{"detail": "Request body too large (max 1MB)."}',
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)

app.add_middleware(LimitBodySizeMiddleware)
```

---

## ISS-005 — In-Memory Rate Limiter Resets on Restart

**File:** `scripts/web/server.py`  
**Severity:** P1  
**Risk:** An attacker who triggers a server restart (crash, deploy, OOM kill)
immediately gets a fresh rate limit window with zero recorded requests.

### The Problem

```python
# scripts/web/server.py — current
_ratelimit_store: dict[str, list[float]] = {}
# This dict lives in process memory.
# Any restart = clean slate.
```

### The Fix — Option A: SQLite-backed (zero new dependencies)

Reuse the existing SQLite infrastructure already in `core/database.py`:

```python
# scripts/web/server.py
import time
import sqlite3
from pathlib import Path

_RL_DB = Path.home() / ".widdx" / "ratelimit.db"

def _rl_init():
    with sqlite3.connect(_RL_DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS ratelimit (
                key   TEXT NOT NULL,
                ts    REAL NOT NULL
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_rl_key_ts ON ratelimit(key, ts)")

def _rl_check(key: str, max_requests: int = 60, window: int = 60) -> bool:
    """Returns True if the request is allowed."""
    now = time.time()
    cutoff = now - window
    with sqlite3.connect(_RL_DB) as con:
        con.execute("DELETE FROM ratelimit WHERE ts < ?", (cutoff,))
        count = con.execute(
            "SELECT COUNT(*) FROM ratelimit WHERE key = ? AND ts >= ?",
            (key, cutoff)
        ).fetchone()[0]
        if count >= max_requests:
            return False
        con.execute("INSERT INTO ratelimit VALUES (?, ?)", (key, now))
    return True

_rl_init()
```

### The Fix — Option B: Redis-backed (if Redis is available)

```python
import redis
_redis = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)

def _rl_check(key: str, max_requests: int = 60, window: int = 60) -> bool:
    pipe = _redis.pipeline()
    now_ms = int(time.time() * 1000)
    pipe.zremrangebyscore(key, 0, now_ms - window * 1000)
    pipe.zadd(key, {str(now_ms): now_ms})
    pipe.zcard(key)
    pipe.expire(key, window * 2)
    _, _, count, _ = pipe.execute()
    return count <= max_requests
```

**Recommendation:** Use Option A (SQLite) — it requires no new infrastructure
and is consistent with the rest of the project's persistence strategy.

---

## ISS-006 — CORS Too Permissive

**File:** `scripts/api_server.py`  
**Severity:** P1  
**Risk:** Any website can make authenticated cross-origin requests to the API
if the browser has a valid session cookie or if credentials are passed. This
enables CSRF-style attacks from malicious pages.

### The Problem

```python
# scripts/api_server.py — current (development defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` with `allow_credentials=True` is rejected by browsers
per the CORS spec — but some configurations still expose surface area.

### The Fix

Read allowed origins from the environment variable already defined for this
purpose (`WIDDX_CORS_ORIGINS`), with a safe default for local development:

```python
# scripts/api_server.py
import os

_raw_origins = os.environ.get("WIDDX_CORS_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # explicit list, not "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

**Deployment:** Set the environment variable to match your actual frontend URL:

```bash
# Production
export WIDDX_CORS_ORIGINS="https://your-app.example.com"

# Multiple origins
export WIDDX_CORS_ORIGINS="https://app.example.com,https://admin.example.com"
```

---

## ISS-007 — Docker Container Runs as Root

**File:** `Dockerfile`  
**Severity:** P1  
**Risk:** If any process inside the container is compromised, the attacker
operates as root inside the container. Combined with a volume mount or a
misconfigured Docker socket, this can lead to full host compromise.

### The Problem

```dockerfile
# Dockerfile — current (no USER directive)
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "-m", "core"]
# Runs as root by default
```

### The Fix

Add a non-root user before the `CMD` instruction:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN groupadd --gid 1001 widdx \
    && useradd --uid 1001 --gid widdx --shell /bin/bash --create-home widdx

COPY . .

RUN pip install --no-cache-dir -e .

# Hand off ownership and switch to non-root user
RUN chown -R widdx:widdx /app
USER widdx

CMD ["python", "-m", "core"]
```

**Note on volumes:** If you mount host directories into the container (e.g.
`-v $(pwd):/app`), ensure the host directory is owned by UID 1001 or make it
world-writable. The non-root user cannot write to root-owned mounts.

```bash
# Quick fix for mounted volumes on Linux/macOS
sudo chown -R 1001:1001 ./data
```

---

## Fix Order Recommendation

| Priority | Issue | Why first |
|----------|-------|-----------|
| 1 | ISS-007 Dockerfile USER | One line change, highest impact-to-effort ratio |
| 2 | ISS-006 CORS origins | One env var read, closes a whole attack class |
| 3 | ISS-004 Body size limit | One middleware, protects all endpoints at once |
| 4 | ISS-005 Rate limiter | Requires choosing SQLite vs Redis first |

---

## After This Sprint

With ISS-004 through ISS-007 closed, all 21 issues from the original register
will be resolved. The remaining items are P3 code-quality improvements
(ISS-016 through ISS-023) which carry no security or stability risk and can be
addressed incrementally as part of normal development.
