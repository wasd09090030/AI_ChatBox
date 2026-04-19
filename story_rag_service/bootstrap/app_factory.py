"""FastAPI 应用工厂。"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.client_storage_routes import router as client_storage_router
from api.v2 import router as v2_router
from application.story_generation import shutdown_story_graph_runtime
from bootstrap.config_resolver import resolve_bootstrap_runtime_config
from bootstrap.container import init_services, reset_container
from bootstrap.modules.core import create_database, create_user_manager, ensure_upload_directory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化服务，关闭时释放资源。"""
    logger.info("Starting Story RAG Service...")

    runtime_config = resolve_bootstrap_runtime_config()
    db = create_database(database_path=runtime_config.database_path)
    logger.info("Database initialized at %s", db.db_path)

    user_manager = create_user_manager(db=db)
    service_container = init_services(user_manager=user_manager)
    app.state.services = service_container
    app.state.user_manager = user_manager
    logger.info("Story RAG Service started successfully!")

    try:
        yield
    finally:
        logger.info("Shutting down Story RAG Service...")
        await shutdown_story_graph_runtime()
        reset_container()


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title="Story RAG Service",
        description="Interactive story generation service using RAG",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        if request.url.path.startswith("/api/v2"):
            response.headers["X-API-Version"] = "v2"

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s elapsed_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    app.include_router(v2_router, prefix="/api/v2", tags=["Story RAG v2"])
    app.include_router(client_storage_router, prefix="/api", tags=["client-storage"])

    runtime_config = resolve_bootstrap_runtime_config()
    upload_dir = ensure_upload_directory(upload_dir=runtime_config.upload_dir)
    app.mount("/files/FileUpload", StaticFiles(directory=str(upload_dir)), name="file_uploads")

    @app.get("/")
    async def root():
        return {
            "service": "Story RAG Service",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "api": "/api/v2",
        }

    return app
