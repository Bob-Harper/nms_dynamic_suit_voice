from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from interface.panels.widgets.buildcard import build_card


class RuntimeManagementWidget(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card, card_layout = build_card("RUNTIME BEHAVIOR")
        card_layout.addWidget(
            QLabel(
                "These values affect the file watcher while the application is running. "
                "Changes are stored now and take effect the next time the watcher starts."
            )
        )
        card_layout.addWidget(QLabel("Filesystem watcher poll interval (seconds)"))

        runtime = self.config.environment.setdefault("runtime", {})
        self.poll_interval_spin = QDoubleSpinBox()
        self.poll_interval_spin.setRange(0.01, 5.0)
        self.poll_interval_spin.setSingleStep(0.05)
        self.poll_interval_spin.setDecimals(2)
        self.poll_interval_spin.setValue(
            float(runtime.get("check_interval", 0.1))
        )
        card_layout.addWidget(self.poll_interval_spin)

        layout.addWidget(card)
        layout.addStretch()

    def gather_settings(self):
        runtime = self.config.environment.setdefault("runtime", {})
        runtime["check_interval"] = self.poll_interval_spin.value()
