"""Central configuration. Change here, not in the code."""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # project root (app/ → root)
CSV_PATH = BASE_DIR / "data/user" / "readlang-data.txt"  # user drops export here
CEFR_PATH = BASE_DIR / "data" / "cefr_mega_dataset.csv"  # optional, for CEFR
WEB_DIR = BASE_DIR / "web"  # html pages
STATIC_DIR = BASE_DIR / "static"  # js/css assets
HOST = "127.0.0.1"
PORT = 8000
DEBUG = False

# SRS thresholds (in days). Change via /api/settings later.
MATURE_DAYS = 21
YOUNG_DAYS = 1
