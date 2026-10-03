"""Environment-backed application configuration."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent


class Config:
    DEBUG = os.getenv("LIFEGRAPH_DEBUG", "false").lower() == "true"
    HOST = os.getenv("LIFEGRAPH_HOST", "127.0.0.1")
    PORT = int(os.getenv("LIFEGRAPH_PORT", "5000"))
    DATABASE_PATH = os.getenv(
        "LIFEGRAPH_DATABASE_PATH",
        str(BACKEND_DIR / "instance" / "lifegraph.db"),
    )
    FRONTEND_DIR = PROJECT_DIR / "frontend"
