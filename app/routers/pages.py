from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "状态"})


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "title": "设置"})


@router.get("/tunnels", response_class=HTMLResponse)
def tunnels(request: Request):
    return templates.TemplateResponse("tunnels.html", {"request": request, "title": "隧道"})


@router.get("/preview", response_class=HTMLResponse)
def preview(request: Request):
    return templates.TemplateResponse("preview.html", {"request": request, "title": "配置预览"})
