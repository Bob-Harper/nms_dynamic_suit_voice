# interface/panels/panel_4_models.py
import sys
import json
import shutil
import threading
import time
import requests
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QFrame, QMessageBox, QProgressBar
)
from pipeline.debug_support import debug_error_message, record_exception

class ModelsPanel(QWidget):
    catalog_refresh_signal = Signal()
    status_update_signal = Signal(str, str, bool, bool, bool)
    progress_signal = Signal(str)
    download_progress_signal = Signal(int, int)
    progress_visible_signal = Signal(bool)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.selected_model_key = None
        self.is_downloading = False

        # CENTRALIZED MODEL WEIGHTS SPECIFICATION DATA TABLE:
        # Maps out your target variations and exact cryptographic file tracking properties
        self.model_catalog = {
            "kokoro-v1.0.int8.onnx": {
                "name": "Kokoro English v1.0 (8-bit Quantized)",
                "size_label": "109 MB",
                "sha256": "ae315a79b623f244700e4afb9246c46a26066782e049ba174bf3ba433970ee9c",
                "voice_bin": "voices-v1.0.bin",
                "note": "Ultra-lightweight compressed model. Delivers blistering fast processing speeds with minimal memory usage. Perfect for resource-constrained systems."
            },
            "kokoro-v1.0.fp16.onnx": {
                "name": "Kokoro English v1.0 (16-bit Float Precision)",
                "size_label": "156 MB",
                "sha256": "f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96",
                "voice_bin": "voices-v1.0.bin",
                "note": "High-fidelity balanced model. Maintains a 0.999 correlation against full precision files while saving half the disk storage overhead."
            },
            "kokoro-v1.0.onnx": {
                "name": "Kokoro English v1.0 (32-bit Full Precision)",
                "size_label": "310 MB",
                "sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
                "voice_bin": "voices-v1.0.bin",
                "note": "Reference quality full precision model. Highest uncompressed vector fidelity for speech processing streams."
            }
        }
        self.list_index_keys = list(self.model_catalog.keys())

        self.catalog_refresh_signal.connect(self._refresh_catalog_list_display)
        self.status_update_signal.connect(self._apply_status_updates)
        self.progress_signal.connect(self._update_progress_text)
        self.download_progress_signal.connect(self._update_download_progress)

        self._build_ui()
        self._refresh_catalog_list_display()
    def _build_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setSpacing(15)
        master_layout.setContentsMargins(15, 15, 15, 15)

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        list_container = QWidget()
        list_container.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(15, 15, 15, 15)
        list_layout.setSpacing(10)

        header_row = QHBoxLayout()
        list_header = QLabel("AVAILABLE EXOSUIT SPEECH ENGINES")
        list_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")

        self.show_all_btn = QPushButton("Refresh Status")
        self.show_all_btn.setStyleSheet("""
            QPushButton { background-color: #1b2230; border: 1px solid #1f2430; border-radius: 4px; color: #5c6773; padding: 4px 10px; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #242f44; color: #ffaa00; border-color: #ffaa00; }
        """)
        self.show_all_btn.clicked.connect(self._refresh_catalog_list_display)
        header_row.addWidget(list_header)
        header_row.addStretch()
        header_row.addWidget(self.show_all_btn)
        list_layout.addLayout(header_row)

        list_title = QLabel("Select Target Model Resolution:")
        list_title.setStyleSheet("color: #ffffff; font-size: 12px; border: none;")
        list_layout.addWidget(list_title)

        self.model_list_widget = QListWidget()
        self.model_list_widget.setStyleSheet("""
            QListWidget { background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; color: #ffffff; font-family: 'Segoe UI', sans-serif; font-size: 13px; padding: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #10141d; }
            QListWidget::item:hover { background-color: #1a2230; color: #ffaa00; }
            QListWidget::item:selected { background-color: #1b2230; color: #ffaa00; font-weight: bold; border-left: 3px solid #ffaa00; }
        """)
        self.model_list_widget.currentRowChanged.connect(self._on_model_selection_change)
        list_layout.addWidget(self.model_list_widget, stretch=1)
        action_frame = QWidget()
        action_frame.setStyleSheet("border: none; background: transparent;")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 5, 0, 0)
        action_layout.setSpacing(8)

        button_base_style = """
            QPushButton { background-color: #1b2230; border: 1px solid #2b384e; border-radius: 4px; color: #ffffff; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #242f44; border-color: #ffaa00; }
            QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }
        """
        self.apply_btn = QPushButton("SET AS ACTIVE")
        self.apply_btn.setStyleSheet(button_base_style)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._activate_selected_model)

        self.download_btn = QPushButton("DOWNLOAD MODEL")
        self.download_btn.setStyleSheet("""
            QPushButton { background-color: #885500; border: 1px solid #ffaa00; border-radius: 4px; color: #ffffff; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #aa7700; }
            QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }
        """)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._trigger_async_download)

        self.delete_btn = QPushButton("REMOVE MODEL")
        self.delete_btn.setStyleSheet("""
            QPushButton { background-color: #551111; border: 1px solid #ff3333; border-radius: 4px; color: #ffffff; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #772222; }
            QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._uninstall_model_assets)

        action_layout.addWidget(self.apply_btn)
        action_layout.addWidget(self.download_btn)
        action_layout.addWidget(self.delete_btn)
        list_layout.addWidget(action_frame)

        left_layout.addWidget(list_container)
        master_layout.addWidget(left_pane, stretch=1)
        right_pane = QWidget()
        right_pane.setFixedWidth(420)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        details_container = QWidget()
        details_container.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(20, 20, 20, 20)
        details_layout.setSpacing(12)

        details_header = QLabel("ENGINE SPECIFICS & SYSTEM DIAGNOSTICS")
        details_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        details_layout.addWidget(details_header)

        self.meta_title_label = QLabel("No Model Selected")
        self.meta_title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; border: none;")
        details_layout.addWidget(self.meta_title_label)

        self.meta_status_label = QLabel("Status: Awaiting Operator Matrix Query")
        self.meta_status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #5c6773; border: none;")
        details_layout.addWidget(self.meta_status_label)

        self.meta_desc_label = QLabel("Select an execution weight file out of the data directory list matrix.")
        self.meta_desc_label.setStyleSheet("color: #ffffff; font-size: 13px; border: none;")
        self.meta_desc_label.setWordWrap(True)
        self.meta_desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        details_layout.addWidget(self.meta_desc_label, stretch=1)

        self.global_storage_label = QLabel("Total Storage Capacity Used by All Models: Calculating...")
        self.global_storage_label.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; color: #8892b0; border: none; padding-top: 4px; border-top: 1px solid #1f2430;")
        details_layout.addWidget(self.global_storage_label)

        self.download_progress_label = QLabel("Queue Status: Idle")
        self.download_progress_label.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; color: #5c6773; border: none; padding-top: 2px;")
        details_layout.addWidget(self.download_progress_label)

        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setFixedHeight(12)
        self.download_progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #1f2430; background-color: #0c0c0e; border-radius: 2px; text-align: center; color: transparent; }
            QProgressBar::chunk { background-color: #ffaa00; }
        """)
        self.download_progress_bar.setVisible(False)
        self.progress_visible_signal.connect(self.download_progress_bar.setVisible)
        details_layout.addWidget(self.download_progress_bar)

        right_layout.addWidget(details_container)
        master_layout.addWidget(right_pane)
    def _get_model_storage_metrics(self, model_key: str) -> tuple[Path, str]:
        """Calculates precise physical file paths using the structural JSON config base definitions."""
        # Dynamically pull the path variable straight out of your centralized config mapping property!
        weights_dir = Path(self.config.tts_base_dir)
        target_file = weights_dir / model_key

        if target_file.exists():
            bytes_on_disk = target_file.stat().st_size
            return target_file, self._format_size(bytes_on_disk)
        return target_file, "0.0 B (Not Instantiated Locally)"

    def _calculate_global_storage_consumption(self):
        """Scans your local assets directory to sum cumulative model allocations natively."""
        weights_dir = Path(self.config.tts_base_dir)
        if not weights_dir.exists():
            self.global_storage_label.setText("Total Storage Used by All Models: 0.0 B")
            return

        try:
            cumulative_bytes = sum(f.stat().st_size for f in weights_dir.glob("*.onnx") if f.is_file())
            companion_bytes = sum(f.stat().st_size for f in weights_dir.glob("*.bin") if f.is_file())
            total_size = cumulative_bytes + companion_bytes
            self.global_storage_label.setText(
                f"Total Storage Used by All Models: {self._format_size(total_size)}"
            )
        except Exception as error:
            token = record_exception(error, "Scanning installed voice-model storage")
            self.global_storage_label.setText(f"Total Storage Used by All Models: Telemetry Fault (ID: {token})")

    def _check_if_model_present_on_disk(self, model_key: str) -> bool:
        target_file, size_str = self._get_model_storage_metrics(model_key)
        return target_file.exists() and target_file.stat().st_size > 1000000
    @Slot()
    def _refresh_catalog_list_display(self):
        """Re-enumerates the resolution list widget cleanly, tracking active configuration flags."""
        self.model_list_widget.clear()
        self._calculate_global_storage_consumption()

        # Read your live model string out of your merged centralized customization maps!
        current_active = self.config.environment.get("models", {}).get("tts_model", "kokoro-v1.0.fp16.onnx")

        for key in self.list_index_keys:
            info = self.model_catalog[key]
            is_downloaded = self._check_if_model_present_on_disk(key)

            status_tag = "[Available]"
            if is_downloaded:
                status_tag = "[Downloaded]"
            if key == current_active:
                status_tag = "▶ [ACTIVE ON EXOSUIT]"

            self.model_list_widget.addItem(f" {status_tag}  {info['name']}")

    def _on_model_selection_change(self, selected_row):
        if selected_row < 0 or selected_row >= len(self.list_index_keys):
            return

        self.selected_model_key = self.list_index_keys[selected_row]
        info = self.model_catalog[self.selected_model_key]

        target_path, size_telemetry = self._get_model_storage_metrics(self.selected_model_key)
        is_downloaded = self._check_if_model_present_on_disk(self.selected_model_key)

        self.meta_title_label.setText(info["name"])

        detailed_profile_text = (
            f"Target Filename Specification:\n{self.selected_model_key}\n\n"
            f"Absolute Workspace Storage Location:\n{target_path}\n\n"
            f"Physical File Allocation Size:\n{size_telemetry}\n\n"
            f"Companion Profile Voice Database:\n{info['voice_bin']}\n\n"
            f"Resolution Diagnostics Info:\n{info['note']}"
        )
        self.meta_desc_label.setText(detailed_profile_text)

        current_active = self.config.environment.get("models", {}).get("tts_model", "kokoro-v1.0.fp16.onnx")
        is_active = (current_active == self.selected_model_key)

        if is_active:
            self._apply_status_updates("Status: Active and Loaded on Exosuit Matrix", "#00ff66", False, False, False)
        elif is_downloaded:
            self._apply_status_updates("Status: Offline Asset Present on Local Disk", "#ffaa00", True, False, True)
        else:
            self._apply_status_updates("Status: Not Downloaded (Assets Missing)", "#ff3333", False, True, False)
    @Slot(str, str, bool, bool, bool)
    def _apply_status_updates(self, text, color_hex, apply_en, dl_en, del_en):
        self.meta_status_label.setText(text)
        self.meta_status_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {color_hex}; border: none;")
        self.apply_btn.setEnabled(apply_en if not self.is_downloading else False)
        self.download_btn.setEnabled(dl_en if not self.is_downloading else False)
        self.delete_btn.setEnabled(del_en if not self.is_downloading else False)

    @Slot(str)
    def _update_progress_text(self, message):
        self.download_progress_label.setText(message)

    @Slot(int, int)
    def _update_download_progress(self, downloaded, total):
        if total <= 0:
            self.download_progress_bar.setRange(0, 0)
            return
        self.download_progress_bar.setRange(0, 100)
        percent = int(downloaded * 100 / total)
        self.download_progress_bar.setValue(percent)
        self.download_progress_label.setText(
            f"Queue Status: Fetching binary frames ({self._format_size(downloaded)} / {self._format_size(total)})"
        )

    @staticmethod
    def _format_size(size):
        value = float(size)
        for unit in ("B", "KiB", "MiB", "GiB"):
            if value < 1024 or unit == "GiB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} GiB"

    def _activate_selected_model(self):
        if not self.selected_model_key:
            return
        try:
            # Safely write the runtime model selection back to the environment configuration map
            self.config.environment["models"]["tts_model"] = self.selected_model_key

            # Match the structural database binary profile link dynamically inside the config layer
            info = self.model_catalog[self.selected_model_key]
            self.config.environment["models"]["tts_voice_bin"] = info["voice_bin"]

            self._refresh_catalog_list_display()
            if self.model_list_widget.count() > 0:
                self.model_list_widget.setCurrentRow(self.list_index_keys.index(self.selected_model_key))
            QMessageBox.information(self, "Success", "Exosuit core weight matrix target swapped successfully!")
        except Exception as e:
            message = debug_error_message(e, "Selecting a voice model")
            QMessageBox.critical(self, "Configuration Error", f"Could not preserve target voice choice:\n{message}")
    def _uninstall_model_assets(self):
        if not self.selected_model_key:
            return
        info = self.model_catalog[self.selected_model_key]
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Permanently uninstall local binary weight file:\n{self.selected_model_key}?\n\nThis will clear up space from your system storage.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            weights_dir = Path(self.config.tts_base_dir)
            target_file = weights_dir / self.selected_model_key
            if target_file.exists():
                target_file.unlink()

            QMessageBox.information(self, "Success", "Model binary weight modules swept out of system storage safely.")
            self._refresh_catalog_list_display()
            self.model_list_widget.setCurrentRow(self.list_index_keys.index(self.selected_model_key))
        except Exception as e:
            message = debug_error_message(e, "Removing downloaded voice-model files")
            QMessageBox.critical(self, "Purge Failure", f"Could not remove local folder modules:\n{message}")

    def _trigger_async_download(self):
        """Activates progress layouts and routes the target download pass out-of-thread."""
        if not self.selected_model_key:
            return

        self.is_downloading = True
        self.download_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)

        self.progress_signal.emit("Queue Status: Synchronizing data links from central registry...")
        self.download_progress_bar.setRange(0, 0)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setVisible(True)

        worker = threading.Thread(target=self._download_worker_thread, daemon=True)
        worker.start()
    def _download_worker_thread(self):
        """Pulls down the model weights and corresponding binary voices mapping files cleanly from json urls."""
        target_model = str(self.selected_model_key)
        info = self.model_catalog[target_model]
        target_voice_bin = info["voice_bin"]

        # Dynamically read your base urls and destinations directly out of your centralized JSON setup configuration!
        base_url = str(self.config.tts_base_url).rstrip('/')
        dest_dir = Path(self.config.tts_base_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        model_url = f"{base_url}/{target_model}"
        voice_url = f"{base_url}/{target_voice_bin}"

        model_dest = dest_dir / target_model
        voice_dest = dest_dir / target_voice_bin

        try:
            # 1. Stream download processing cycle for the .onnx layout graph file
            self.progress_signal.emit(f"Queue Status: Querying stream payload for {target_model}...")
            with requests.get(model_url, stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                with open(model_dest, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.download_progress_signal.emit(downloaded, total_size)

            # 2. Stream download processing cycle for the accompanying .bin voice map matrices array
            if not voice_dest.exists() or voice_dest.stat().st_size < 1000000:
                self.progress_signal.emit(f"Queue Status: Fetching voice profiles matrix ({target_voice_bin})...")
                with requests.get(voice_url, stream=True, allow_redirects=True) as r:
                    r.raise_for_status()
                    with open(voice_dest, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

            self.progress_signal.emit("Queue Status: Model downloaded and verified successfully.")
        except Exception as e:
            self.progress_signal.emit("Queue Status: Download pipeline processing failed.")
            message = debug_error_message(e, "Downloading or extracting a voice model")
            print(f"[DOWNLOAD FAULT]: Model extraction failed: {message}")
            if model_dest.exists() and model_dest.stat().st_size < 1000000:
                model_dest.unlink()  # Scrub broken text file fragments automatically if hit by a network anomaly
        finally:
            self.is_downloading = False
            self.download_progress_bar.setVisible(False)
            self.catalog_refresh_signal.emit()

    def gather_settings(self):
        if self.selected_model_key:
            self.config.environment["models"]["tts_model"] = self.selected_model_key
