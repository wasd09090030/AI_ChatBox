"""故事 RAG 主应用入口。

基于 FastAPI 提供交互式故事生成服务，融合 RAG、LangChain 与 ChromaDB。
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from pathlib import Path
from config import settings
from api.service_context import init_services, reset_container
from api.v2 import router as v2_router
from api.client_storage_routes import router as client_storage_router
from graph.story_v2.story_graph import close_story_graph
from services.database import Database
from services.user_manager import UserManager

# 配置全局日志格式。
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# 模块日志记录器，用于输出运行诊断信息。
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化服务，关闭时释放资源。"""
    logger.info("Starting Story RAG Service...")

    db = Database(settings.database_path)
    logger.info(f"Database initialized at {settings.database_path}")

    user_manager = UserManager(db=db)

    service_container = init_services(user_manager=user_manager)
    app.state.services = service_container

    app.state.user_manager = user_manager
    logger.info("Story RAG Service started successfully!")

    try:
        yield
    finally:
        logger.info("Shutting down Story RAG Service...")
        await close_story_graph()
        reset_container()


# 创建 FastAPI 应用实例。
app = FastAPI(
    title="Story RAG Service",
    description="Interactive story generation service using RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 配置 CORS。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应收敛为明确来源列表。
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """注入 request_id，并记录请求-响应耗时链路。"""
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

# 挂载业务路由。
app.include_router(v2_router, prefix="/api/v2", tags=["Story RAG v2"])
app.include_router(client_storage_router, prefix="/api", tags=["client-storage"])

# 暴露上传文件静态访问路径。
_upload_dir = Path(settings.database_path).parent / "FileUpload"
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files/FileUpload", StaticFiles(directory=str(_upload_dir)), name="file_uploads")


@app.get("/")
async def root():
    """根路径健康信息。"""
    return {
        "service": "Story RAG Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "api": "/api/v2"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info"
    )
