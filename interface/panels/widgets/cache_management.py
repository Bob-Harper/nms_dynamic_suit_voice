# interface/panels/widgets/cache_management.py
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interface.panels.widgets.buildcard import build_card
from pipeline.debug_support import debug_error_message, record_exception


class CacheManagementWidget(QWidget):
    CACHE_PATH_KEYS = (
        "cache_root",
        "temp_wem_dir",
        "temp_wav_dir",
        "quick_cache_dir",
    )

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.project_root = Path(__file__).resolve().parents[3]
        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card, card_layout = build_card("EXOSUIT CACHE AND STORAGE")

        # Single compact row: Cached files | Storage usage | Refresh button
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.cache_files_label = QLabel("Cached files: Calculating...")
        self.cache_size_label = QLabel("Storage usage: Calculating...")
        self.refresh_button = QPushButton("REFRESH STORAGE STATUS")
        self.refresh_button.setStyleSheet("padding: 6px 12px; font-weight: bold;")
        self.refresh_button.clicked.connect(self.refresh_stats)
        self.refresh_button = QPushButton("REFRESH STORAGE STATUS")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #2b5b84;
                border: 1px solid #66b2ff;
                padding-top: 10px;
                padding-bottom: 6px;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_stats)

        stats_row.addWidget(self.cache_files_label)
        stats_row.addWidget(self.cache_size_label)
        stats_row.addStretch()
        stats_row.addWidget(self.refresh_button)
        card_layout.addLayout(stats_row)

        # Compact horizon row: Label + SpinBox side-by-side
        horizon_row = QHBoxLayout()
        horizon_row.setSpacing(10)

        cache_settings = self.config.environment.setdefault("runtime", {})
        self.cache_horizon_spin = QSpinBox()
        self.cache_horizon_spin.setRange(1, 64)
        self.cache_horizon_spin.setFixedWidth(80)
        self.cache_horizon_spin.setValue(int(cache_settings.get("quick_cache_max", 16)))

        horizon_row.addWidget(QLabel("Maximum quick-cache variations per voice line:"))
        horizon_row.addWidget(self.cache_horizon_spin)
        horizon_row.addStretch()
        card_layout.addLayout(horizon_row)

        self.cache_policy_label = QLabel()
        self.cache_policy_label.setWordWrap(True)
        self.cache_policy_label.setStyleSheet("color: #8a99ad; font-size: 11px;")
        card_layout.addWidget(self.cache_policy_label)

        layout.addWidget(card)

    def _cache_directories(self):
        paths = self.config.environment.get("paths", {})
        directories = []
        candidates = []
        for key in self.CACHE_PATH_KEYS:
            value = paths.get(key, "cache" if key == "cache_root" else None)
            if not value:
                continue
            directory = Path(value)
            if not directory.is_absolute():
                directory = self.project_root / directory
            directory = directory.resolve()
            candidates.append(directory)
        for directory in sorted(candidates, key=lambda path: len(path.parts)):
            if not any(root == directory or root in directory.parents for root in directories):
                directories.append(directory)
        return directories

    def refresh_stats(self):
        try:
            file_count = 0
            total_bytes = 0
            for directory in self._cache_directories():
                if not directory.exists():
                    continue
                for path in directory.rglob("*"):
                    if not path.is_symlink() and path.is_file():
                        file_count += 1
                        total_bytes += path.stat().st_size
            self.cache_files_label.setText(f"Cached files: {file_count:,}")
            self.cache_size_label.setText(
                f"Storage usage: {total_bytes / (1024 * 1024):.1f} MB"
            )
        except OSError as error:
            self.cache_files_label.setText("Cached files: unavailable")
            token = record_exception(error, "Scanning cache storage")
            self.cache_size_label.setText(
                f"Storage scan failed: {error} (DEBUG TOKEN = {token})"
            )

        horizon = self.cache_horizon_spin.value()
        self.cache_policy_label.setText(
            f"Quick cache limit: {horizon} variations per voice line. "
            "Temporary WEM, WAV, and quick-cache files are included in storage totals."
        )

    def purge_all_caches(self) -> bool:
        directories = self._cache_directories()
        targets = "\n".join(str(path) for path in directories)
        answer = QMessageBox.question(
            self,
            "Confirm cache purge",
            "Permanently remove the contents of these configured cache folders?\n\n"
            f"{targets or '(No cache folders are configured)'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False

        try:
            paths = self.config.environment.get("paths", {})
            mod_dir_value = paths.get("mod_dir")
            mod_dir = Path(mod_dir_value) if mod_dir_value else None
            if mod_dir is not None and not mod_dir.is_absolute():
                mod_dir = self.project_root / mod_dir
            if mod_dir is not None:
                mod_dir = mod_dir.resolve()
            for directory in directories:
                if directory == directory.parent:
                    raise ValueError(f"Refusing to purge a filesystem root: {directory}")
                if directory == self.project_root:
                    raise ValueError(
                        f"Refusing to purge the application folder: {directory}"
                    )
                if mod_dir is not None and (
                    directory == mod_dir
                    or directory in mod_dir.parents
                    or mod_dir in directory.parents
                ):
                    raise ValueError(
                        f"Cache folder overlaps the mod folder: {directory}"
                    )

            removed_count = 0
            for directory in directories:
                if not directory.exists():
                    continue
                for item in directory.iterdir():
                    if item.is_symlink() or item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                    removed_count += 1
        except (OSError, ValueError) as error:
            message = debug_error_message(error, "Purging cache storage")
            QMessageBox.critical(
                self, "Cache purge failed",
                f"Could not clear cache storage:\n{message}"
            )
            self.refresh_stats()
            return False

        self.refresh_stats()
        QMessageBox.information(
            self,
            "Cache purge complete",
            f"Removed {removed_count} cache entries.",
        )
        return True

    def gather_settings(self):
        runtime = self.config.environment.setdefault("runtime", {})
        runtime["quick_cache_max"] = self.cache_horizon_spin.value()
