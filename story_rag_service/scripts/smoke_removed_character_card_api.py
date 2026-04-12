"""验证旧版 character-card API 不再暴露的冒烟测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# 变量作用：路径变量 PROJECT_ROOT，用于定位文件系统资源。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app


def main() -> None:
    """功能：处理 main。"""
    client = TestClient(app)

    removed = client.get("/api/v2/roleplay/character-cards")
    assert removed.status_code == 404, removed.text

    print("[OK] legacy character-card API removed smoke passed")


if __name__ == "__main__":
    main()