from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.public_router import public_v1_router


app = FastAPI(
    title="Ledger Normalization API",
    version="1.0.0",
)

# RapidAPI-friendly CORS (fine for a public JSON API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# REQUIRED FOR RAPIDAPI + RENDER PROBES
# -------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "service": "ledger-normalization-api", "gateway": "ready"}


@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------------------------------
# PUBLIC /v1 ROUTES (RapidAPI Contract)
# -------------------------------------------------
# This is the missing piece that caused your 404 on /v1/ledger/summarize
app.include_router(public_v1_router)
