from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# -------------------------------------------------
# App setup
# -------------------------------------------------

app = FastAPI(
    title="Ledger Normalization API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# REQUIRED FOR RAPIDAPI GATEWAY
# -------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ledger-normalization-api",
        "gateway": "ready",
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------------------------------
# EXISTING API ROUTES (KEEP /v1 PREFIX)
# -------------------------------------------------

@app.get("/v1/health")
def v1_health():
    return {"status": "ok"}

@app.post("/v1/normalize")
def normalize(
    payload: dict,
    x_rapidapi_key: Optional[str] = Header(None),
):
    # RapidAPI ALWAYS injects this header when gateway is working
    if not x_rapidapi_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-RapidAPI-Key",
        )

    # Stub response (replace with your real logic if needed)
    return {
        "normalized": True,
        "input": payload,
    }
