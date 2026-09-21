from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler

app = FastAPI(title=settings.project_name)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"]

if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.add_exception_handler(AppException, app_exception_handler)
app.include_router(api_router)

from pathlib import Path
from fastapi.staticfiles import StaticFiles
app.mount("/api/assets", StaticFiles(directory=Path(__file__).parent / "assets"), name="assets")
