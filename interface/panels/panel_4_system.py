from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from interface.panels.widgets.cache_management import CacheManagementWidget
from interface.panels.widgets.path_management import PathManagementWidget
from interface.panels.widgets.runtime_settings import RuntimeManagementWidget
from interface.panels.widgets.update_management import UpdateManagementWidget


class SystemPanel(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._acknowledged = False
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
            "SYSTEM SETTINGS\n\n"
            "Most users do not need to change these settings. Incorrect paths, "
            "runtime values, or update choices can prevent the application or "
            "mod from working as expected.\n\n"
            "Continue only if you understand the setting you are changing. "
            "Changes are saved to configuration files and may require restarting "
            "the application."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background-color: #141923; border: 1px solid #ffaa00; "
            "border-radius: 6px; padding: 18px; color: #ffffff;"
        )

        self.acknowledgement = QCheckBox(
            "I understand that changing these settings may have unintended results."
        )
        self.continue_button = QPushButton("CONTINUE TO SYSTEM SETTINGS")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self._open_settings)
        self.acknowledgement.toggled.connect(self.continue_button.setEnabled)

        gate_layout.addWidget(warning)
        gate_layout.addSpacing(12)
        gate_layout.addWidget(self.acknowledgement)
        gate_layout.addWidget(self.continue_button)
        gate_layout.addStretch()
        self.pages.addWidget(self.gate_page)

        self.settings_page = QTabWidget()
        self.update_widget = UpdateManagementWidget(self.config)
        self.cache_widget = CacheManagementWidget(self.config)
        self.runtime_widget = RuntimeManagementWidget(self.config)
        self.path_widget = PathManagementWidget(self.config)
        self.settings_page.addTab(self.update_widget, "Updates")
        self.settings_page.addTab(self.cache_widget, "Cache")
        self.settings_page.addTab(self.runtime_widget, "Runtime")
        self.settings_page.addTab(self.path_widget, "Paths")
        self.pages.addWidget(self.settings_page)

    def _open_settings(self):
        if not self.acknowledgement.isChecked():
            return
        self._acknowledged = True
        self.pages.setCurrentWidget(self.settings_page)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acknowledged:
            self.pages.setCurrentWidget(self.gate_page)

    def gather_settings(self):
        self.path_widget.gather_settings()
        self.cache_widget.gather_settings()
        self.runtime_widget.gather_settings()
        self.update_widget.gather_settings()
        self.cache_widget.refresh_stats()
