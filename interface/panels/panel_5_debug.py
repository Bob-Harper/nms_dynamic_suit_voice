import json
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from pipeline.debug_support import (
    extract_debug_token,
    load_debug_report,
    record_exception,
)


class DebugPanel(QWidget):
    settings_requested = Signal(str)

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.catalog = {"tokens": {}, "generic": {}, "support": {}}
        self._settings_target = None
        self._load_catalog()
        self._build_ui()

    def _load_catalog(self):
        catalog_path = Path(__file__).resolve().parents[2] / "data" / "debug_tokens.json"
        try:
            with catalog_path.open("r", encoding="utf-8") as catalog_file:
                self.catalog = json.load(catalog_file)
        except (OSError, json.JSONDecodeError) as error:
            self.catalog_error = str(error)
            self.catalog_error_token = record_exception(
                error, "Loading the debug-token help catalog"
            )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Enhanced Debug")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(
            QLabel(
                "Enter a debug token from an error message to see likely causes and "
                "repair steps."
            )
        )

        input_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Example: DEBUG TOKEN = JSONCONFIG_NP")
        self.token_input.returnPressed.connect(self.lookup_token)
        input_row.addWidget(self.token_input, 1)

        self.lookup_button = QPushButton("Look up token")
        self.lookup_button.clicked.connect(self.lookup_token)
        input_row.addWidget(self.lookup_button)
        layout.addLayout(input_row)

        self.status_label = QLabel("Error reports are stored locally and are never uploaded automatically.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        if getattr(self, "catalog_error", None):
            self.status_label.setText(
                f"The help catalog could not be loaded. DEBUG TOKEN = "
                f"{self.catalog_error_token}"
            )

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Token help and diagnostic details will appear here.")
        layout.addWidget(self.details, 1)

        action_row = QHBoxLayout()
        self.settings_button = QPushButton("Open related settings")
        self.settings_button.setEnabled(False)
        self.settings_button.clicked.connect(self._open_related_settings)
        action_row.addWidget(self.settings_button)

        self.issue_button = QPushButton("Open GitHub issues")
        self.issue_button.clicked.connect(self._open_github_issues)
        action_row.addWidget(self.issue_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

    def lookup_token(self):
        token = extract_debug_token(self.token_input.text())
        if token is None:
            self.status_label.setText("Enter a token, or paste the complete DEBUG TOKEN line.")
            self.details.clear()
            self.settings_button.setEnabled(False)
            self._settings_target = None
            return

        report_error_token = None
        try:
            report = load_debug_report(token) if token.startswith("DSV-") else None
        except OSError as error:
            report = None
            report_error_token = record_exception(
                error, f"Reading local diagnostic report {token}"
            )
        related_token = report.get("related_token") if report else None
        entry = self.catalog.get("tokens", {}).get(related_token or token)
        if entry is None:
            entry = self.catalog.get("generic", {})
        self._show_help(token, entry, related_token)

        if report is not None:
            self._show_local_report(report)
            self.status_label.setText(
                f"Found local diagnostic report for {token}. Details stay on this computer."
            )
        elif report_error_token:
            self.status_label.setText(
                f"Could not read the local report. DEBUG TOKEN = {report_error_token}"
            )
        elif token.startswith("DSV-"):
            self.status_label.setText(
                f"No local report was found for {token}. It may have been produced on another computer."
            )
        else:
            self.status_label.setText(f"Help entry for {token}.")
        self.settings_button.setEnabled(bool(entry.get("settings_target")))
        self._settings_target = entry.get("settings_target")

    def _show_help(self, token, entry, related_token=None):
        lines = [
            f"{entry.get('title', 'Debug token')}",
            f"Token: {token}",
        ]
        if related_token:
            lines.append(f"Help category: {related_token}")
        lines.extend(["", entry.get("summary", "")])
        if entry.get("likely_causes"):
            lines.extend(["", "Likely causes:"])
            lines.extend(f"- {cause}" for cause in entry["likely_causes"])
        if entry.get("steps"):
            lines.extend(["", "What to try:"])
            lines.extend(f"{index}. {step}" for index, step in enumerate(entry["steps"], 1))
        if getattr(self, "catalog_error", None):
            lines.extend(["", f"Help catalog could not be loaded: {self.catalog_error}"])
        self.details.setPlainText("\n".join(lines))

    def _show_local_report(self, report):
        self.details.appendPlainText(
            "\n\nLocal diagnostic report"
            f"\nWhen: {report.get('timestamp', 'unknown')}"
            f"\nWhere: {report.get('context', 'unknown')}"
            f"\nError: {report.get('exception_type', 'Exception')}: "
            f"{report.get('message', '')}"
        )
        traceback_text = report.get("traceback")
        if traceback_text:
            self.details.appendPlainText(f"\nTechnical details:\n{traceback_text}")

    def _open_related_settings(self):
        if self._settings_target:
            self.settings_requested.emit(self._settings_target)

    def _open_github_issues(self):
        url = self.catalog.get("support", {}).get(
            "issues_url",
            "https://github.com/Bob-Harper/nms_dynamic_suit_voice/issues",
        )
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(
                self,
                "Could not open GitHub",
                f"Open this URL in a browser: {url}",
            )

    def gather_settings(self):
        pass
