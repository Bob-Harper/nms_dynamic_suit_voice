# interface/panels/panel_6_debug.py
import sys
import json
import shutil
from pathlib import Path
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QStackedWidget, QComboBox
)
from interface.panels.widgets.shared import build_card

from interface.panels.widgets.path_management import PathManagementWidget
from interface.panels.widgets.cache_management import CacheManagementWidget
from interface.panels.widgets.runtime_settings import RuntimeManagementWidget


class DebugPanel(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config

        # DATA-DRIVEN ASSIGNMENTS: Zero hardcoding, straight from config.py
        self.tokens_file = Path(__file__).resolve().parents[2] / "data" / "debug_tokens.json"
        self.reports_file = self.config.debug_reports_path

        self.static_issues_catalog = {}
        self.generic_fallback = {}


        # Read static definitions database on launch
        if self.tokens_file.exists():
            try:
                with open(self.tokens_file, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                self.static_issues_catalog = token_data.get("tokens", {})
                self.generic_fallback = token_data.get("generic", {})
            except Exception as e:
                print(f"[DEBUG ENVIRONMENT]: Failed to parse debug_tokens.json: {e}", file=sys.stderr)

        self._build_ui()

    def _build_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setSpacing(15)
        master_layout.setContentsMargins(15, 15, 15, 15)

        # ==============================================================================
        # LEFT COLUMN: THE INCIDENT DROPDOWN, INPUT, & TEXT LOG VIEW
        # ==============================================================================
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        entry_card, entry_layout = build_card("Diagnostic Token / Error Code Input")

        # THE LIVE HISTORY SELECTOR: Populates from debug_reports.jsonl
        entry_layout.addWidget(QLabel("Select From Recent Local Incident Events:"))
        self.history_combo = QComboBox()
        self.history_combo.setStyleSheet("""
            QComboBox {
                background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px;
                padding: 6px; color: #ffffff; font-family: 'Consolas', monospace; font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #0c0c0e; color: #ffffff; selection-background-color: #1b2230; }
        """)
        self.history_combo.currentIndexChanged.connect(self._on_history_selection_changed)
        entry_layout.addWidget(self.history_combo)

        entry_layout.addWidget(QLabel("Or Paste / Type Manual Code Entry:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter code (e.g. DSV2WEMN_FND) or paste dynamic session token...")
        self.token_input.setStyleSheet("""
            QLineEdit {
                background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px;
                padding: 8px; color: #ffffff; font-family: 'Consolas', monospace;
            }
        """)
        entry_layout.addWidget(self.token_input)

        self.lookup_btn = QPushButton("RUN COGNITION MATRIX LOOKUP")
        self.lookup_btn.setStyleSheet("""
            QPushButton { background-color: #1b2230; border: 1px solid #2b384e; color: white; padding: 10px; font-weight: bold; font-family: 'Consolas', monospace; }
            QPushButton:hover { background-color: #242f44; border-color: #ffaa00; }
        """)
        self.lookup_btn.clicked.connect(self._execute_matrix_lookup)
        entry_layout.addWidget(self.lookup_btn)
        left_layout.addWidget(entry_card)

        left_layout.addWidget(QLabel("Diagnostic Analysis & Operational Run Logs:"))
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        self.report_display.setStyleSheet("""
            QTextEdit { background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; color: #ffaa00; font-family: 'Consolas', monospace; font-size: 11px; }
        """)
        left_layout.addWidget(self.report_display)

        # Global external support anchor button layout block
        self.support_btn = QPushButton("OPEN GITHUB PROJECT ISSUES PAGE")
        self.support_btn.setStyleSheet("""
            QPushButton {
                background-color: #004477;
                border: 1px solid #0088cc;
                border-radius: 4px;
                color: #ffffff;
                padding: 10px;
                font-weight: bold;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #005588;
                border-color: #ffaa00;
            }
        """)
        self.support_btn.clicked.connect(self._open_github_issues_browser)
        left_layout.addWidget(self.support_btn)


        master_layout.addWidget(left_pane, stretch=1)

        # ==============================================================================
        # RIGHT COLUMN: THE DYNAMIC CONTAINER FOR DECOUPLED WIDGETS
        # ==============================================================================
        right_pane = QWidget()
        right_pane.setFixedWidth(440)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.widget_stack = QStackedWidget()
        right_layout.addWidget(self.widget_stack)

        # Page Index 0: Standby Default View Card
        self.standby_page = QWidget()
        sb_layout = QVBoxLayout(self.standby_page)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        card_sb, layout_sb = build_card("Targeted Repair Deck")

        self.desc_sb = QLabel("Awaiting operational query lookup. Matched configuration controls will embed themselves here for adjustments.")
        self.desc_sb.setStyleSheet("color: #5c6773; font-size: 12px; border: none;")
        self.desc_sb.setWordWrap(True)

        layout_sb.addWidget(self.desc_sb)
        layout_sb.addStretch()
        sb_layout.addWidget(card_sb)
        self.widget_stack.addWidget(self.standby_page)

        # Page Index 1
        self.path_page = QWidget()
        pr_layout = QVBoxLayout(self.path_page)
        pr_layout.setContentsMargins(0, 0, 0, 0)
        self.shared_path_widget = PathManagementWidget(self.config)
        pr_layout.addWidget(self.shared_path_widget)
        self.widget_stack.addWidget(self.path_page)

        # Page Index 2
        self.cache_page = QWidget()
        cc_layout = QVBoxLayout(self.cache_page)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        self.shared_cache_widget = CacheManagementWidget(self.config)
        cc_layout.addWidget(self.shared_cache_widget)
        self.widget_stack.addWidget(self.cache_page)

        # Page Index 3
        self.runtime_page = QWidget()
        rt_layout = QVBoxLayout(self.runtime_page)
        rt_layout.setContentsMargins(0, 0, 0, 0)
        self.shared_runtime_widget = RuntimeManagementWidget(self.config)
        rt_layout.addWidget(self.shared_runtime_widget)
        self.widget_stack.addWidget(self.runtime_page)

        master_layout.addWidget(right_pane)

    def showEvent(self, event):
        """Triggers every single time the user clicks onto this tab, re-scanning the ledger for live updates."""
        super().showEvent(event)
        self._refresh_incident_history_dropdown()

    def _refresh_incident_history_dropdown(self):
        """Reads local logs in reverse. Seeds the active log from the config template if missing."""
        import json
        import shutil

        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItem(" -- Select a recent logged incident to autofill lookup --", "")

        # RECOVERY COMPLIANCE LINK: Read templates out of config using the resolved path structure
        if not self.reports_file.exists() or self.reports_file.stat().st_size == 0:
            # Use fallback default template
            project_root = self.reports_file.parents[1]
            template_file = project_root / "config" / "default_debug_reports.jsonl"

            if template_file.exists():
                try:
                    self.reports_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(str(template_file), str(self.reports_file))
                    print("[LAUNCHER HARDWARE]: Local incident ledger seeded successfully from config template.")

                    # RECOVERY PASS: Re-enable signals and re-trigger once so the freshly
                    # copied template reads instantly on first boot
                    self.history_combo.blockSignals(False)
                    self._refresh_incident_history_dropdown()
                    return
                except Exception as e:
                    print(f"[LAUNCHER WARNING]: Failed to clone config welcome log: {e}", file=sys.stderr)

        else:
            try:
                scanned_items = []
                with open(self.reports_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            report = json.loads(line)
                            token = report.get("token")
                            context = report.get("context", "Unknown Incident")
                            timestamp = report.get("timestamp", "")

                            # Clean up ISO timestamp into a neat short clock readout [15:42:01]
                            time_part = timestamp.split("T")[-1][:8] if "T" in timestamp else "00:00:00"

                            if token:
                                display_text = f"[{time_part}] {context} ({token})"
                                scanned_items.append((display_text, token))
                        except json.JSONDecodeError:
                            continue

                # Reverse the list so the most recent error is immediately sitting right at the top
                for display_text, token in reversed(scanned_items[-20:]): # Keep the last 20 reports
                    self.history_combo.addItem(display_text, token)
            except Exception as e:
                print(f"[DEBUG ENVIRONMENT]: Dropdown refresh failed: {e}", file=sys.stderr)

        self.history_combo.blockSignals(False)


    def _on_history_selection_changed(self, index):
        """Fires when the user clicks an item in the combo dropdown list."""
        if index <= 0:
            return
        # Grab the token data attached to the selection item slot
        associated_token = self.history_combo.itemData(index)
        if associated_token:
            self.token_input.setText(associated_token)
            # Run the matrix search execution loop
            self._execute_matrix_lookup()

    def _execute_matrix_lookup(self):
        """Processes known static list checks first, then falls back to session log file parsing."""
        code = self.token_input.text().strip().upper()
        if not code:
            self.report_display.setText(">> Input field blank. Provide an error signature to execute lookup cycles.")
            self.widget_stack.setCurrentWidget(self.standby_page)
            return

        # ====================================================
        # EVALUATE STATIC ENUMERATED CODES FIRST
        # ====================================================
        if code in self.static_issues_catalog:
            item = self.static_issues_catalog[code]

            causes_text = "\n".join(f"- {c}" for c in item.get("likely_causes", []))
            steps_text = "\n".join(f"- {s}" for s in item.get("steps", []))

            self.report_display.setText(
                f"DIAGNOSTIC REPORT: CODE {code}\n"
                f"==================================================\n"
                f"SUMMARY: {item.get('title', '')}\n"
                f"DETAILS: {item.get('summary', '')}\n\n"
                f"POTENTIAL ROOT CAUSES:\n{causes_text}\n\n"
                f"RECOMMENDED SYSTEM CORRECTIONS:\n{steps_text}"
            )

            target = str(item.get("settings_target", "")).lower()
            if "path" in target:
                self.widget_stack.setCurrentWidget(self.path_page)
            elif "cache" in target:
                self.widget_stack.setCurrentWidget(self.cache_page)
            elif "runtime" in target:
                self.widget_stack.setCurrentWidget(self.runtime_page)
            else:
                self.widget_stack.setCurrentWidget(self.standby_page)
            return

        # ====================================================
        # FALLBACK TO SCANNED SESSION EXCEPTION LOGS
        # ====================================================
        from pipeline.debug_support import load_debug_report
        report = load_debug_report(code)
        if not report:
            generic_causes = "\n".join(f"- {c}" for c in self.generic_fallback.get("likely_causes", []))
            generic_steps = "\n".join(f"- {s}" for s in self.generic_fallback.get("steps", []))

            self.report_display.setText(
                f"UNKNOWN ENCOUNTERED ANOMALY: REJECTION PROFILE\n"
                f"==================================================\n"
                f"SUMMARY: {self.generic_fallback.get('title', 'Unknown code signature')}\n"
                f"DETAILS: {self.generic_fallback.get('summary', '')}\n\n"
                f"POTENTIAL ROOT CAUSES:\n{generic_causes}\n\n"
                f"RECOMMENDED REPAIR STEPS:\n{generic_steps}"
            )
            self.widget_stack.setCurrentWidget(self.standby_page)
            return

        # Explicit unhandled trace readout
        self.report_display.setText(
            f"DYNAMIC RUNTIME FAILURE BLOCK REPORT\n"
            f"==================================================\n"
            f"Session Timestamp: {report.get('timestamp')}\n"
            f"Context Failure Domain: {report.get('context')}\n"
            f"Exception Code Pattern: {report.get('exception_type')}\n"
            f"Message Stream: {report.get('message')}\n\n"
            f"Raw Kernel Stack Traceback:\n{report.get('traceback')}"
        )

        context_str = str(report.get("context", "")).lower()
        message_str = str(report.get("message", "")).lower()

        if "path" in context_str or "directory" in context_str or "file" in message_str:
            self.widget_stack.setCurrentWidget(self.path_page)
        elif "cache" in context_str or "allocation" in context_str:
            self.widget_stack.setCurrentWidget(self.cache_page)
        elif "runtime" in context_str or "loop" in context_str:
            self.widget_stack.setCurrentWidget(self.runtime_page)
        else:
            self.widget_stack.setCurrentWidget(self.standby_page)

    def gather_settings(self):
        active = self.widget_stack.currentWidget()
        if active == self.path_page:
            self.shared_path_widget.gather_settings()
        elif active == self.cache_page:
            self.shared_cache_widget.gather_settings()
        elif active == self.runtime_page:
            self.shared_runtime_widget.gather_settings()

    def _open_github_issues_browser(self):
        """Launches the default system web browser straight to the repository help tracking page."""
        import webbrowser

        # Pull the repository URL string straight out of config object variables
        updates_cfg = self.config.environment.get("updates", {})

        try:
            webbrowser.open(self.config.support_url)
            self.report_display.append(f"\n>> External communication interface deployed: Browsing to {self.config.support_url}")
        except Exception as e:
            self.report_display.append(f"\n>> Failed to deploy web browser execution thread: {e}")
