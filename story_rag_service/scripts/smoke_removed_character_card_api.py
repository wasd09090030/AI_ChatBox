"""验证旧版 character-card API 不再暴露的冒烟测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# 将仓库根目录加入导入路径，确保脚本可直接以 `python scripts/...` 方式运行。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app


def main() -> None:
    """确认已下线的 legacy character-card 路由返回 404。"""
    client = TestClient(app)

    removed = client.get("/api/v2/roleplay/character-cards")
    assert removed.status_code == 404, removed.text

    print("[OK] legacy character-card API removed smoke passed")


if __name__ == "__main__":
    main()