from __future__ import annotations
import json
from pathlib import Path
from typing import Dict
from .config import I18N_DIR, LANG_DEFAULT

_translations: Dict[str, Dict[str, str]] = {}
_current_lang = LANG_DEFAULT

def load_translations():
    global _translations
    for code in ("en", "ar"):
        path = I18N_DIR / f"{code}.json"
        if path.exists():
            _translations[code] = json.loads(path.read_text(encoding="utf-8"))


def set_language(lang_code: str):
    global _current_lang
    _current_lang = lang_code if lang_code in _translations else "en"


def t(key: str) -> str:
    table = _translations.get(_current_lang) or {}
    return table.get(key, key)