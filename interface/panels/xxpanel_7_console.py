# interface/panels/panel_7_console.py
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton

class ConsolePanel(QWidget):
    # Native PySide6 signal to marshal background string lines safely to the main GUI thread
    log_signal = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

        # Connect internal signal handling loops safely across thread boundaries
        self.log_signal.connect(self._append_console_log)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # HEADER LAYOUT Row
        header_layout = QHBoxLayout()
        header_title = QLabel("LIVE EXOSUIT TELEMETRY STREAM")
        header_title.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px;")

        self.clear_btn = QPushButton("CLEAR TERMINAL")
        self.clear_btn.setStyleSheet("""
            QPushButton { background-color: #1b2230; border: 1px solid #1f2430; border-radius: 4px; color: #5c6773; padding: 4px 12px; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #551111; border-color: #ff3333; color: #ffffff; }
        """)
        self.clear_btn.clicked.connect(self._clear_terminal_view)

        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        layout.addLayout(header_layout)

        # MONOSPACE TERMINAL VIEWPORT SCREEN
        self.console_view = QTextEdit()
        self.console_view.setReadOnly(True)
        self.console_view.setStyleSheet("""
            QTextEdit {
                background-color: #0c0c0e;
                border: 1px solid #1f2430;
                border-radius: 4px;
                color: #00ff66;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        self.console_view.append(">> Nexus.QUEEG Kernel Logging System Online.\n>> Awaiting telemetry matrix hooks...")
        layout.addWidget(self.console_view, stretch=1)

    @Slot(str)
    def _append_console_log(self, text):
        """Thread-safe receiver appending logs and locking scrollbars to the bottom line."""
        self.console_view.append(f">> {text}")
        self.console_view.ensureCursorVisible()

    def _clear_terminal_view(self):
        self.console_view.clear()
        self.console_view.append(">> Terminal logs cleared by operator directive.")

    def gather_settings(self):
        pass
