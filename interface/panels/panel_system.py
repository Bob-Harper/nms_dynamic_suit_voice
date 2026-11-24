# interface/panels/panel_4_system.py
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
from interface.panels.widgets.path_management import PathManagementWidget
from interface.panels.widgets.runtime_settings import RuntimeManagementWidget
from pipeline.localization import t


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

        warning = QLabel(t("UI_PANEL_SYSTEM_001"))
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background-color: #141923; border: 1px solid #ffaa00; border-radius: 6px; padding: 18px; color: #ffffff;"
        )

        self.acknowledgement = QCheckBox(t("UI_PANEL_SYSTEM_002"))
        self.continue_button = QPushButton(t("UI_PANEL_SYSTEM_003"))
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self._open_settings)
        self.acknowledgement.toggled.connect(self.continue_button.setEnabled)

        gate_layout.addWidget(warning)
        gate_layout.addSpacing(12)
        gate_layout.addWidget(self.acknowledgement)
        gate_layout.addWidget(self.continue_button)
        gate_layout.addStretch()
        self.pages.addWidget(self.gate_page)

        # The System configuration book no longer contains the update widget
        self.settings_page = QTabWidget()
        self.runtime_widget = RuntimeManagementWidget(self.config)
        self.path_widget = PathManagementWidget(self.config)

        self.settings_page.addTab(self.runtime_widget, t("UI_PANEL_SYSTEM_004"))
        self.settings_page.addTab(self.path_widget, t("UI_PANEL_SYSTEM_005"))
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
        if self._acknowledged:
            pass
        else:
            self.pages.setCurrentWidget(self.gate_page)

    def gather_settings(self):
        self.path_widget.gather_settings()
        self.runtime_widget.gather_settings()
