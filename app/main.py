from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import DEFAULT_HOST, DEFAULT_PORT
from app.routers import api_settings, api_tunnels, api_xray, pages

app = FastAPI(title="b_client_xray")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(api_settings.router)
app.include_router(api_tunnels.router)
app.include_router(api_xray.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=False)
