from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "embedder.service:app",
        host=settings.embedder_host,
        port=settings.embedder_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
