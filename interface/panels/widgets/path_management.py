# interface/panels/widgets/path_management.py
from pathlib import Path
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interface.panels.widgets.buildcard import build_card
from pipeline.localization import t


class PathManagementWidget(QWidget):
    PATH_FIELD_KEYS = (
        ("mod_dir", "UI_WIDGET_PATH_003"),
        ("cache_root", "UI_WIDGET_PATH_004"),
        ("temp_wem_dir", "UI_WIDGET_PATH_005"),
        ("temp_wav_dir", "UI_WIDGET_PATH_006"),
        ("quick_cache_dir", "UI_WIDGET_PATH_007"),
    )

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.project_root = Path(__file__).resolve().parents[3]
        self.path_edits = {}
        self._build_ui()

    def _field_label(self, key: str) -> str:
        loc_key = dict(self.PATH_FIELD_KEYS)[key]
        return t(loc_key)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card, card_layout = build_card(t("UI_WIDGET_PATH_001"))
        card_layout.addWidget(QLabel(t("UI_WIDGET_PATH_002")))

        paths = self.config.environment.setdefault("paths", {})
        for key, loc_key in self.PATH_FIELD_KEYS:
            card_layout.addWidget(QLabel(t(loc_key)))
            row = QHBoxLayout()
            default_value = "cache" if key == "cache_root" else ""
            edit = QLineEdit(str(paths.get(key, default_value)))
            browse = QPushButton(t("UI_WIDGET_PATH_008"))
            browse.clicked.connect(
                lambda checked=False, field=key, line_edit=edit: self._browse(
                    field, line_edit
                )
            )
            row.addWidget(edit)
            row.addWidget(browse)
            card_layout.addLayout(row)
            self.path_edits[key] = edit

        layout.addWidget(card)
        layout.addStretch()

    def _browse(self, key, edit):
        current = edit.text().strip()
        current_path = Path(current)
        if not current_path.is_absolute():
            current_path = self.project_root / current_path
        initial_dir = (
            str(current_path) if current_path.is_dir() else str(Path.home())
        )
        selected = QFileDialog.getExistingDirectory(
            self,
            t("UI_WIDGET_PATH_009", field_name=self._field_label(key)),
            initial_dir,
        )
        if selected:
            edit.setText(selected)

    def gather_settings(self):
        paths = self.config.environment.setdefault("paths", {})
        values = {key: edit.text().strip() for key, edit in self.path_edits.items()}
        for key, value in values.items():
            if not value:
                raise ValueError(
                    t("UI_WIDGET_PATH_010", field_name=self._field_label(key))
                )

        mod_dir = Path(values["mod_dir"])
        if not mod_dir.is_absolute():
            mod_dir = self.project_root / mod_dir
        if not mod_dir.is_dir():
            raise ValueError(t("UI_WIDGET_PATH_011", mod_dir=mod_dir))

        for key, edit in self.path_edits.items():
            paths[key] = values[key]
