from __future__ import annotations

import importlib
import os
from typing import Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_VERSION = os.getenv("PUBLIC_API_VERSION", "public 1.0.0")

# Direct-to-Render lock (for non-RapidAPI traffic)
PROVIDER_SECRET_ENV = "PROVIDER_SECRET"
PROVIDER_SECRET_HEADER = "X-Provider-Secret"


def _get_provider_secret() -> Optional[str]:
    val = os.getenv(PROVIDER_SECRET_ENV)
    if not val:
        return None
    val = val.strip()
    return val or None


def _is_rapidapi_request(request: Request) -> bool:
    """
    Detect requests coming from RapidAPI's gateway/proxy.
    """
    h = request.headers

    # Strong signal (when enabled in RapidAPI Gateway firewall settings)
    if h.get("x-rapidapi-proxy-secret"):
        return True

    # Common signals for RapidAPI requests
    if h.get("x-rapidapi-key") and h.get("x-rapidapi-host"):
        return True

    return False


def _load_public_router() -> Tuple[object, str]:
    """
    Load the FastAPI APIRouter from api.public_router regardless of what
    the variable is named inside that file.

    Supported exported names (we try all of these):
      - router
      - public_router
      - api_router
      - public_v1_router   (your repo’s current name)
    """
    mod = importlib.import_module("api.public_router")

    for name in ("router", "public_router", "api_router", "public_v1_router"):
        candidate = getattr(mod, name, None)
        if candidate is not None:
            return candidate, name

    available = [k for k in dir(mod) if not k.startswith("_")]
    raise RuntimeError(
        "api.public_router loaded, but no APIRouter export found. "
        "Expected one of: router, public_router, api_router, public_v1_router. "
        "Exports found: %s" % (available,)
    )


app = FastAPI(
    title="Ledger Normalization API",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (RapidAPI does not require this, but browser clients might)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    """
    Rules:
      - /health is always public (for Render health checks)
      - All /v1/* routes:
          - If request comes via RapidAPI → allow (RapidAPI handles auth)
          - Else → require X-Provider-Secret (blocks direct Render abuse)
    """
    path = request.url.path or ""

    # Public health check
    if path == "/health":
        return await call_next(request)

    # Only protect /v1 routes
    if not path.startswith("/v1/"):
        return await call_next(request)

    # Allow CORS preflight
    if request.method.upper() == "OPTIONS":
        return await call_next(request)

    # RapidAPI traffic: trust RapidAPI auth
    if _is_rapidapi_request(request):
        return await call_next(request)

    # Direct traffic: must provide provider secret
    secret = _get_provider_secret()
    if not secret:
        # Fail closed if misconfigured
        return JSONResponse(
            status_code=503,
            content={"detail": "Server misconfigured: %s is not set." % PROVIDER_SECRET_ENV},
        )

    provided = request.headers.get(PROVIDER_SECRET_HEADER, "")
    if provided != secret:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized."})

    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


# Router include (robust to variable naming inside api/public_router.py)
_public_router, _router_name = _load_public_router()
app.include_router(_public_router, prefix="/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
