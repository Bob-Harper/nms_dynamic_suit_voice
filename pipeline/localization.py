# pipeline/localization.py
import json
from pathlib import Path
from typing import Dict
from pipeline.debug_support import debug_error_message, record_exception

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
LOCALIZATION_DIR = PROJECT_ROOT / "data" / "localization"
USER_CUSTOMIZATION_PATH = PROJECT_ROOT / "config" / "user_customization.json"

_IGNORED_KEYS = {"Default0", "BOF", "EOF"}
_active_language: str = "en_us"
_translations: Dict[str, str] = {}
_fallback_translations: Dict[str, str] = {}


# Note that the error messages in this file are not localized - if there is an error message it is because it CANNOT localize so there is no point.
def _detect_initial_language() -> str:
    """Reads the preferred locale from user_customization.json before SuitVoiceConfig loads."""
    if not USER_CUSTOMIZATION_PATH.exists():
        print(f"[LOCALIZATION WARNING] Config not found at {USER_CUSTOMIZATION_PATH}; defaulting to 'en_us'.")
        return "en_us"
    try:
        with open(USER_CUSTOMIZATION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return "en_us"
        project_cfg = data.get("project")
        lang = (
            (project_cfg.get("ui_locale") if isinstance(project_cfg, dict) else None)
            or data.get("ui_locale")
            or "en_us"
        )
        return str(lang).strip().lower() or "en_us"
    except Exception as error:
        record_exception(error, "Detecting initial localization setting")
        print(f"[LOCALIZATION ERROR] {debug_error_message(error, 'Reading locale config')}")
        return "en_us"


def _flatten_strings(data: dict, prefix: str = "") -> Dict[str, str]:
    """Flattens string leaves from nested dicts while skipping ignored keys."""
    flat: Dict[str, str] = {}
    for key, value in data.items():
        if key in _IGNORED_KEYS:
            continue
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, str):
            if value.strip():
                flat[full_key] = value
        elif isinstance(value, dict):
            flat.update(_flatten_strings(value, full_key))
    return flat


def _load_language_pack(language: str) -> Dict[str, str]:
    """Merges all *.json files from data/localization/<language>/."""
    merged: Dict[str, str] = {}
    lang_dir = LOCALIZATION_DIR / language
    if not lang_dir.is_dir():
        return merged

    for json_file in sorted(lang_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if isinstance(raw_data, dict):
                merged.update(_flatten_strings(raw_data))
        except Exception as err:
            print(f"[LOCALIZATION] Failed to parse {json_file.name}: {err}")

    return merged


def set_language(language: str) -> None:
    """Switches the active language and reloads translation dictionaries."""
    global _active_language, _translations, _fallback_translations

    normalized = (language or "en_us").strip().lower()
    _active_language = normalized

    if not _fallback_translations:
        _fallback_translations = _load_language_pack("en_us")

    if normalized == "en_us":
        _translations = dict(_fallback_translations)
    else:
        loaded = _load_language_pack(normalized)
        _translations = {**_fallback_translations, **loaded}


def get_language() -> str:
    return _active_language


def t(key: str, **kwargs) -> str:
    """
    Translates a localization key and formats any named placeholders.
    Falls back to English, then to the raw key if missing or malformed.
    """
    text = _translations.get(key) or _fallback_translations.get(key) or key
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, ValueError):
        fallback = _fallback_translations.get(key)
        if fallback and fallback != text:
            try:
                return fallback.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text


# Initialize immediately on module import so early UI startup has strings ready
set_language(_detect_initial_language())