from __future__ import annotations
import os
from pathlib import Path

APP_NAME = "Lazordy Inventory"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"
SECRETS_DIR = BASE_DIR / "secrets"
I18N_DIR = BASE_DIR / "app" / "i18n"

DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
SECRETS_DIR.mkdir(exist_ok=True)

SQLITE_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite:///{SQLITE_PATH}"

# Used for token-based protections (PDF password, etc.)
DEFAULT_SECRET_KEY = "change-this-in-.env"
SECRET_KEY = os.getenv("LAZORDY_SECRET_KEY", DEFAULT_SECRET_KEY)

LOGO_PATH = ASSETS_DIR / "logo.png"
THEME_QSS_PATH = ASSETS_DIR / "theme.qss"

LANG_DEFAULT = os.getenv("LAZORDY_LANG", "en")