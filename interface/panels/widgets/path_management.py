# interface\panels\widgets\path_management.py
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


class PathManagementWidget(QWidget):
    PATH_FIELDS = ( # TODO: json this bitch in with the actual paths
        ("mod_dir", "No Man's Sky Mod Directory"),
        ("cache_root", "Cache and Temporary Storage Directory"),
        ("temp_wem_dir", "Temporary WEM Directory"),
        ("temp_wav_dir", "Temporary WAV Directory"),
        ("quick_cache_dir", "Quick Cache Directory"),
    )

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.project_root = Path(__file__).resolve().parents[3]
        self.path_edits = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card, card_layout = build_card("PLATFORM PATH MANAGEMENT")
        card_layout.addWidget(
            QLabel(
                "Choose the folders used by the mod and its local caches. "
                "Path changes take effect after restarting the application."
            )
        )

        paths = self.config.environment.setdefault("paths", {})
        for key, title in self.PATH_FIELDS:
            card_layout.addWidget(QLabel(title))
            row = QHBoxLayout()
            default_value = "cache" if key == "cache_root" else ""
            edit = QLineEdit(str(paths.get(key, default_value)))
            browse = QPushButton("Browse...")
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
            f"Select {dict(self.PATH_FIELDS)[key]}",
            initial_dir,
        )
        if selected:
            edit.setText(selected)

    def gather_settings(self):
        paths = self.config.environment.setdefault("paths", {})
        values = {key: edit.text().strip() for key, edit in self.path_edits.items()}
        for key, value in values.items():
            if not value:
                raise ValueError(f"{dict(self.PATH_FIELDS)[key]} cannot be empty.")

        mod_dir = Path(values["mod_dir"])
        if not mod_dir.is_absolute():
            mod_dir = self.project_root / mod_dir
        if not mod_dir.is_dir():
            raise ValueError(f"The No Man's Sky mod folder does not exist:\n{mod_dir}")

        for key, edit in self.path_edits.items():
            paths[key] = values[key]
