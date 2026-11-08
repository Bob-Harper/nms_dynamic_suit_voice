# pipeline/debug_support.py
import json
import re
import sys
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtGui import QGuiApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEBUG_REPORTS_PATH = PROJECT_ROOT / "logs" / "debug_reports.jsonl"
_REPORT_LOCK = threading.Lock()
_MARKED_TOKEN_PATTERN = re.compile(
    r"DEBUG\s+TOKEN\s*=\s*([A-Z0-9_-]+)", re.IGNORECASE
)
_INCIDENT_TOKEN_PATTERN = re.compile(r"\bDSV-[A-F0-9]{10}\b", re.IGNORECASE)
_PLAIN_TOKEN_PATTERN = re.compile(r"[A-Z][A-Z0-9_-]{2,}", re.IGNORECASE)


def extract_debug_token(text: str) -> str | None:
    match = _INCIDENT_TOKEN_PATTERN.search(text)
    if match is None:
        match = _MARKED_TOKEN_PATTERN.search(text)
    if match is not None:
        return match.group(1).upper() if match.lastindex else match.group(0).upper()
    candidate = text.strip()
    if _PLAIN_TOKEN_PATTERN.fullmatch(candidate):
        return candidate.upper()
    return None


def record_exception(
    error: BaseException, context: str, related_token: str | None = None
) -> str:
    token = f"DSV-{uuid.uuid4().hex[:10].upper()}"

    record = {
        "token": token,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "related_token": related_token,
        "exception_type": type(error).__name__,
        "message": str(error),
        "traceback": "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        ),
    }
    try:
        DEBUG_REPORTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _REPORT_LOCK, DEBUG_REPORTS_PATH.open("a", encoding="utf-8") as report_file:
            report_file.write(json.dumps(record, ensure_ascii=True) + "\n")
    except OSError as write_error:
        print(
            f"DEBUG TOKEN = {token} >> Could not save local debug report: "
            f"{write_error}",
            file=sys.stderr,
        )
    return token


def debug_error_message(error: BaseException, context: str) -> str:
    related_token = extract_debug_token(str(error))
    if related_token and related_token.startswith("DSV-"):
        related_token = None
    token = record_exception(error, context, related_token)
    return f"{error}\n\nDEBUG TOKEN = {token}\n(Token key has been logged to the Event Viewer. Open the event log dropdown on the Debug Tab to query logs.)"


def load_debug_report(token: str) -> dict | None:
    if not DEBUG_REPORTS_PATH.exists():
        return None

    with _REPORT_LOCK, DEBUG_REPORTS_PATH.open("r", encoding="utf-8") as report_file:
        found_report = None
        for line in report_file:
            try:
                report = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(report, dict) and report.get("token") == token:
                found_report = report
        return found_report


def install_exception_hooks():
    original_sys_hook = sys.excepthook
    original_thread_hook = threading.excepthook

    def handle_unhandled_exception(exception_type, error, error_traceback):
        if issubclass(exception_type, KeyboardInterrupt):
            original_sys_hook(exception_type, error, error_traceback)
            return
        token = record_exception(error, "Unhandled application exception")
        print(f"DEBUG TOKEN = {token}", file=sys.stderr)
        original_sys_hook(exception_type, error, error_traceback)

    def handle_unhandled_thread_exception(args):
        token = record_exception(
            args.exc_value, "Unhandled background-thread exception"
        )
        print(f"DEBUG TOKEN = {token}", file=sys.stderr)
        original_thread_hook(args)

    sys.excepthook = handle_unhandled_exception
    threading.excepthook = handle_unhandled_thread_exception
