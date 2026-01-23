from __future__ import annotations

from fastapi import FastAPI

from api.public_router import router as public_router


app = FastAPI(
    title="Ledger Normalization API",
    version="public 1.0.0",
)


@app.get("/health", summary="Health")
def health():
    return {"status": "ok"}


# IMPORTANT:
# - NO prefix here
# - This prevents /v1/v1 bugs permanently
app.include_router(public_router)
