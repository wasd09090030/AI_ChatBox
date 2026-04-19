"""故事 RAG 主应用入口。"""

import uvicorn

from bootstrap.app_factory import create_app
from config import settings

app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info"
    )
