# interface/panels/panel_4_models.py
import sys
import json
import shutil
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QFrame, QMessageBox, QProgressBar
)
from pipeline.debug_support import debug_error_message, record_exception

class _TtsDownloadProgress:
    def __init__(self, total, update_callback):
        self.total = total if isinstance(total, int) and total > 0 else 0
        self.downloaded = 0
        self.update_callback = update_callback
        self.last_percent = -1
        self.last_update_time = 0.0
        self.update_callback(0, self.total)

    def update(self, amount):
        self.downloaded += amount
        now = time.monotonic()
        percent = int(self.downloaded * 100 / self.total) if self.total else -1
        if percent != self.last_percent or now - self.last_update_time >= 0.2:
            self.update_callback(self.downloaded, self.total)
            self.last_percent = percent
            self.last_update_time = now

    def close(self):
        pass

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

        self.model_catalog = {
            "tts_models/en/ek1/tacotron2": {
                "name": "Tacotron2 EK1", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Vintage-themed synthetic engine. Great for classic old-school terminal styles."
            },
            "tts_models/en/ljspeech/tacotron2-DDC": {
                "name": "Tacotron2 DDC", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "A highly stable, traditional technical voice layer with excellent clarity."
            },
            "tts_models/en/ljspeech/tacotron2-DCA": {
                "name": "Tacotron2 DCA", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Crisp navigational vocal structure. Provides crisp, distinct alert profiles."
            },
            "tts_models/en/ljspeech/tacotron2-DDC_ph": {
                "name": "Tacotron2 DDC PH (Mod Default)", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "The original baseline fine-tuned vocal core. Natively optimized for real-time play."
            },
            "tts_models/en/ljspeech/glow-tts": {
                "name": "Glow TTS Engine", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Smooth phrasing layout. Exceptional baseline for applying heavy MALE SHIFT profiles!"
            },
            "tts_models/en/ljspeech/speedy-speech": {
                "name": "Speedy Speech Matrix", "gender": "FEMALE", "pacing": "Relaxed (0.60 - 0.75)",
                "note": "Extremely fast output engine. Drop sentence pacing significantly to ensure clarity."
            },
            "tts_models/en/ljspeech/fast_pitch": {
                "name": "Fast Pitch Core", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Energetic, modern synthesis model. Delivers prominent high-tech status readouts."
            },
            "tts_models/en/jenny/jenny": {
                "name": "Jenny (Conversational AI)", "gender": "FEMALE", "pacing": "Relaxed (0.80 - 0.90)",
                "note": "Highly organic natural speech footprint. Best paired with the Clinical Matrix preset."
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

        # ==============================================================================
        # LEFT PANE: CATALOG LIST DIRECTORY & BLUEPRINT TRIGGER BUTTON
        # ==============================================================================
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        list_container = QWidget()
        list_container.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(15, 15, 15, 15)
        list_layout.setSpacing(10)

        # HEADER LAYOUT BLOCK: Hosts title and the blueprint filter side-by-side
        header_row = QHBoxLayout()
        list_header = QLabel("AVAILABLE EXOSUIT SPEECH ENGINES")
        list_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")

        self.show_all_btn = QPushButton("Show All Models")
        self.show_all_btn.setStyleSheet("""
            QPushButton { background-color: #1b2230; border: 1px solid #1f2430; border-radius: 4px; color: #5c6773; padding: 4px 10px; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #242f44; color: #ffaa00; border-color: #ffaa00; }
        """)
        header_row.addWidget(list_header)
        header_row.addStretch()
        header_row.addWidget(self.show_all_btn)
        list_layout.addLayout(header_row)

        list_title = QLabel("Select Active Synthesis Model:")
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

        # ACTIONS CONTROLS BAR Row
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

        # ==============================================================================
        # RIGHT PANE: FIXED-WIDTH DIAGNOSTICS DECK & MATRIX TOTALS
        # ==============================================================================
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

        self.meta_title_label = QLabel("No Engine Selected")
        self.meta_title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; border: none;")
        details_layout.addWidget(self.meta_title_label)

        self.meta_status_label = QLabel("Status: Awaiting Operator Matrix Query")
        self.meta_status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #5c6773; border: none;")
        details_layout.addWidget(self.meta_status_label)

        self.meta_desc_label = QLabel("Select an engine from the list layout to adjust active suit weights.")
        self.meta_desc_label.setStyleSheet("color: #ffffff; font-size: 13px; border: none;")
        self.meta_desc_label.setWordWrap(True)
        self.meta_desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        details_layout.addWidget(self.meta_desc_label, stretch=1)

        # Global Storage Telemetry Readout Bar: Anchored right above progress tracks
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

        # Give the left pane all remaining flexible space so ONLY the left side scales
        master_layout.addWidget(left_pane, stretch=1)
        master_layout.addWidget(right_pane)

    def _get_model_storage_metrics(self, model_key: str) -> tuple[Path, str]:
        """Calculates precise physical file footprints and paths for model targets on disk."""
        local_appdata_path = Path.home() / "AppData" / "Local" / "tts"
        folder_name = model_key.replace("/", "--")
        target_folder = local_appdata_path / folder_name

        if target_folder.exists() and any(target_folder.iterdir()):
            total_bytes = sum(f.stat().st_size for f in target_folder.rglob('*') if f.is_file())
            return target_folder, self._format_size(total_bytes)
        return target_folder, "0.0 B (Not Instantiated Locally)"

    def _calculate_global_storage_consumption(self):
        """Scans the local storage array directory to sum cumulative model asset allocations."""
        local_appdata_path = Path.home() / "AppData" / "Local" / "tts"
        if not local_appdata_path.exists():
            self.global_storage_label.setText("Total Storage Used by All Models: 0.0 B")
            return

        try:
            cumulative_bytes = 0
            for folder in local_appdata_path.iterdir():
                if folder.is_dir() and "tts_models" in folder.name:
                    cumulative_bytes += sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
            self.global_storage_label.setText(
                f"Total Storage Used by All Models: {self._format_size(cumulative_bytes)}"
            )
        except Exception as error:
            token = record_exception(error, "Scanning installed voice-model storage")
            self.global_storage_label.setText(
                f"Total Storage Used by All Models: Telemetry Fault "
                f"(DEBUG TOKEN = {token})"
            )

    def _check_if_model_present_on_disk(self, model_key: str) -> bool:
        target_folder, size_str = self._get_model_storage_metrics(model_key)
        return target_folder.exists() and "Not Instantiated" not in size_str

    @Slot()
    def _refresh_catalog_list_display(self):
        """Re-enumerates the model list tracker rows cleanly, maintaining active profile markers."""
        self.model_list_widget.clear()
        self._calculate_global_storage_consumption()

        current_active = self.config.user_customization.get("tts_model")
        if not current_active:
            env_path = Path(__file__).parent.parent.parent / "config" / "environment_config.json"
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    env_map = json.load(f)
                current_active = env_map.get("models", {}).get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")
            except Exception as error:
                message = debug_error_message(
                    error, "Reading the selected voice model configuration"
                )
                print(f"[MODEL CONFIGURATION ERROR] {message}")
                current_active = "tts_models/en/ljspeech/tacotron2-DDC_ph"

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
            f"Full Identifier Key:\n{self.selected_model_key}\n\n"
            f"Local System Target Path:\n{target_path}\n\n"
            f"Storage Footprint Size:\n{size_telemetry}\n\n"
            f"Vocal Baseline Profile: [{info['gender']}]\n"
            f"Recommended Pacing Bounds: {info['pacing']}\n\n"
            f"Exosuit Tuning Note:\n{info['note']}"
        )
        self.meta_desc_label.setText(detailed_profile_text)

        current_active = self.config.user_customization.get("tts_model")
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
        self.apply_btn.setEnabled(apply_en)
        self.download_btn.setEnabled(dl_en)
        self.delete_btn.setEnabled(del_en)

    @Slot(str)
    def _update_progress_text(self, message):
        self.download_progress_label.setText(message)

    @Slot(int, int)
    def _update_download_progress(self, downloaded, total):
        if total <= 0:
            self.download_progress_bar.setRange(0, 0)
            self.download_progress_label.setText("Queue Status: Downloading model assets (size unavailable)...")
            return

        self.download_progress_bar.setRange(0, 1000)
        self.download_progress_bar.setValue(min(1000, int(downloaded * 1000 / total)))
        self.download_progress_label.setText(
            f"Queue Status: Downloading model assets ({self._format_size(downloaded)} / {self._format_size(total)})"
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
            self.config.user_customization["tts_model"] = self.selected_model_key
            self._refresh_catalog_list_display()
            if self.model_list_widget.count() > 0:
                self.model_list_widget.setCurrentRow(self.list_index_keys.index(self.selected_model_key))
            QMessageBox.information(self, "Success", "Voice engine weights configuration updated successfully!")
        except Exception as e:
            message = debug_error_message(e, "Selecting a voice model")
            QMessageBox.critical(
                self, "Configuration Error",
                f"Could not preserve target voice choice:\n{message}"
            )

    def _uninstall_model_assets(self):
        if not self.selected_model_key:
            return
        info = self.model_catalog[self.selected_model_key]
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Permanently uninstall local files for:\n{info['name']}?\n\nThis will clear up space from your system storage.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            local_appdata_path = Path.home() / "AppData" / "Local" / "tts"
            folder_name = self.selected_model_key.replace("/", "--")
            target_folder = local_appdata_path / folder_name

            if target_folder.exists():
                shutil.rmtree(target_folder)

            QMessageBox.information(self, "Success", "Model weights cleared out of system storage cleanly.")
            self._refresh_catalog_list_display()
            self.model_list_widget.setCurrentRow(self.list_index_keys.index(self.selected_model_key))
        except Exception as e:
            message = debug_error_message(e, "Removing downloaded voice-model files")
            QMessageBox.critical(
                self, "Purge Failure",
                f"Could not remove local folder modules:\n{message}"
            )

    # ==============================================================================
    # ASYNCHRONOUS ENGINE DOWNLOAD HOOKS & LIVE PROGRESS STREAM INTERCEPTORS
    # ==============================================================================
    def _trigger_async_download(self):
        """Activates the progress tracker layout parameters and dispatches the background thread link."""
        if not self.selected_model_key:
            return

        self.download_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)

        self.progress_signal.emit("Queue Status: Synchronizing data assets from registry...")

        self.download_progress_bar.setRange(0, 0)
        self.progress_visible_signal.emit(True)

        worker = threading.Thread(target=self._download_worker_thread, daemon=True)
        worker.start()

    def _download_worker_thread(self):
        target_key = str(self.selected_model_key) if self.selected_model_key else ""
        manage_module = None
        original_tqdm = None
        try:
            from TTS.utils import manage as manage_module
            from TTS.api import TTS

            original_tqdm = manage_module.tqdm

            def progress_factory(*args, **kwargs):
                total = kwargs.get("total")
                if total is None and args:
                    total = args
                return _TtsDownloadProgress(total, self.download_progress_signal.emit)

            manage_module.tqdm = progress_factory
            _warmed_engine = TTS(model_name=target_key, progress_bar=True)

            self.progress_signal.emit("Queue Status: Model downloaded successfully.")
        except Exception as e:
            self.progress_signal.emit("Queue Status: Download pipeline process failed.")
            message = debug_error_message(e, "Downloading or extracting a voice model")
            self.progress_signal.emit(message)
            print(f"[DOWNLOAD FAULT]: Model extraction failed: {message}")
        finally:
            if manage_module is not None and original_tqdm is not None:
                manage_module.tqdm = original_tqdm
            self.progress_visible_signal.emit(False)
            self.catalog_refresh_signal.emit()

    def gather_settings(self):
        if self.selected_model_key:
            self.config.user_customization["tts_model"] = self.selected_model_key
