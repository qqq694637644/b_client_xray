from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("B_CLIENT_DATA_DIR", BASE_DIR / "data"))
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18080
