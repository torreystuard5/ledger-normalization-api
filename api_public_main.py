from __future__ import annotations

import os

from fastapi import FastAPI

from api.public_router import public_v1_router

APP_NAME = "Ledger Normalization API"
APP_VERSION = "1.0.0"


def create_app() -> FastAPI:
    app = FastAPI(title=APP_NAME, version=APP_VERSION)

    # Public (RapidAPI) router only
    app.include_router(public_v1_router)

    return app


app = create_app()
