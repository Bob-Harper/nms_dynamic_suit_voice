# interface/panels/panel_4_system.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QStackedWidget, QTabWidget, QVBoxLayout, QWidget
from interface.panels.widgets.cache_management import CacheManagementWidget
from interface.panels.widgets.path_management import PathManagementWidget
from interface.panels.widgets.runtime_settings import RuntimeManagementWidget

class SystemPanel(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._acknowledged = False
        self._pending_settings_section = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.pages = QStackedWidget()
        layout.addWidget(self.pages)

        self.gate_page = QWidget()
        gate_layout = QVBoxLayout(self.gate_page)
        gate_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        warning = QLabel(
            "SYSTEM DIAGNOSTICS & TUNING CONSOLE\n\n"
            "Altering these low-level pipeline variables, file allocation tables, "
            "or operational path roots can cause severe runtime calculation disruptions "
            "across the cognition matrix engine loops.\n\n"
            "Proceed ONLY if you are tracking specific workspace environmental paths."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background-color: #141923; border: 1px solid #ffaa00; border-radius: 6px; padding: 18px; color: #ffffff;"
        )

        self.acknowledgement = QCheckBox("I accept complete technical oversight over these changes.")
        self.continue_button = QPushButton("CONTINUE TO CRITICAL SYSTEM SETTINGS")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self._open_settings)
        self.acknowledgement.toggled.connect(self.continue_button.setEnabled)

        gate_layout.addWidget(warning)
        gate_layout.addSpacing(12)
        gate_layout.addWidget(self.acknowledgement)
        gate_layout.addWidget(self.continue_button)
        gate_layout.addStretch()
        self.pages.addWidget(self.gate_page)

        # The System configuration book no longer contains the update widget!
        self.settings_page = QTabWidget()
        self.cache_widget = CacheManagementWidget(self.config)
        self.runtime_widget = RuntimeManagementWidget(self.config)
        self.path_widget = PathManagementWidget(self.config)

        self.settings_page.addTab(self.cache_widget, "Cache Table Allocation")
        self.settings_page.addTab(self.runtime_widget, "Runtime Subsystem")
        self.settings_page.addTab(self.path_widget, "System Paths Mapping")
        self.pages.addWidget(self.settings_page)

    def _open_settings(self):
        if not self.acknowledgement.isChecked():
            return
        self._acknowledged = True
        self.pages.setCurrentWidget(self.settings_page)
        if self._pending_settings_section:
            section = self._pending_settings_section.casefold()
            for index in range(self.settings_page.count()):
                if self.settings_page.tabText(index).casefold() == section:
                    self.settings_page.setCurrentIndex(index)
                    break
            self._pending_settings_section = None

    def request_settings(self, section):
        self._pending_settings_section = section
        if self._acknowledged:
            self._open_settings()
        else:
            self.pages.setCurrentWidget(self.gate_page)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acknowledged:
            self.pages.setCurrentWidget(self.gate_page)

    def gather_settings(self):
        self.path_widget.gather_settings()
        self.cache_widget.gather_settings()
        self.runtime_widget.gather_settings()
        self.cache_widget.refresh_stats()
