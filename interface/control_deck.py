# interface/control_deck.py
import sys
import json
import importlib
import hashlib
import threading
import tempfile
from pathlib import Path

# Force-align the execution context to look back up at the main mod root folder
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PySide6.QtCore import Qt, QLockFile, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QMessageBox, QLabel, QFrame, QProgressBar,
    QMenu, QSystemTrayIcon
)
from interface.panels.widgets.config_io import write_json_atomic
from pipeline.debug_support import (
    debug_error_message,
    install_exception_hooks,
    record_exception,
)

class ConfigLoaderWorker(QThread):
    """Asynchronously loads the heavy SuitVoiceConfig configurations off the UI thread."""
    config_loaded_signal = Signal(object)
    config_failed_signal = Signal(str)

    def run(self):
        print("[LAUNCHER BACKGROUND]: Initializing SuitVoiceConfig layers...")
        try:
            from pipeline.config import SuitVoiceConfig
            config_instance = SuitVoiceConfig(init_llm=False)
        except Exception as error:
            self.config_failed_signal.emit(
                debug_error_message(error, "Loading application configuration")
            )
            return
        self.config_loaded_signal.emit(config_instance)

class ExosuitEngineThread(QThread):
    """Natively runs core No Man's Sky filewatcher loop as a worker thread."""
    engine_log_signal = Signal(str)
    status_signal = Signal(str, bool)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.stop_event = threading.Event()

    def run(self):
        try:
            from pipeline.nms_dynamic_suit_voice_pipeline import watch_wems
            watch_wems(self, self.config)
        except Exception as error:
            self.engine_log_signal.emit(
                debug_error_message(error, "Starting or running the background watcher")
            )

    def update_status(self, message, is_ready=False):
        self.status_signal.emit(message, is_ready)

class ControlDeckDashboard(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. LIGHTWEIGHT TEXT READ FOR THE VERSION SIGNATURE
        env_data = {}
        try:
            env_path = project_root / "config" / "environment_config.json"
            with open(env_path, "r", encoding="utf-8") as f:
                env_data = json.load(f)
            meta = env_data.get("project", {})
            v_sig = f"v{meta['version']} ({meta['release_major']}.{meta['release_minor']})"
        except Exception as e:
            # NO FALSE DATA: Signal a clear diagnostic failure in the title bar
            token = record_exception(e, "Reading the application version")
            print(f"[LAUNCHER CRITICAL]: {e} (DEBUG TOKEN = {token})")
            v_sig = f"CONFIG ERROR ({token})"

        icon_path_value = env_data.get("paths", {}).get(
            "icon_image", "assets/nms_dsv.png"
        )
        self.tray_icon_path = Path(icon_path_value)
        if not self.tray_icon_path.is_absolute():
            self.tray_icon_path = project_root / self.tray_icon_path

        self.setWindowTitle(f"NMS Dynamic Suit Voice [{v_sig}]")

        self.resize(960, 850)
        self.setMinimumSize(640, 500)

        self.config = None
        self.engine_thread = None
        self.loader_thread = None
        self._quit_requested = False
        self._allow_close = False
        self._tray_notice_shown = False
        self._engine_error_message = None
        self.notebook = QTabWidget()

        # 2. RUN VISUALS FIRST: Build the UI widgets immediately so they are ready to paint
        self.init_ui()
        self._setup_system_tray()

        # 3. KICK OFF BACKGROUND INITIALIZATION DELAYED
        # Triggers 50ms after the window frame draws, keeping the startup completely unblocked
        QTimer.singleShot(50, self.launch_background_config_loader)

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0c0c0e; }
            QTabWidget::pane { border: 1px solid #1f2430; background-color: #141923; border-radius: 4px; }
            QTabBar::tab {
                background-color: #10141d;
                color: #5c6773;
                border: 1px solid #1f2430;
                padding: 10px 20px;
                font-family: 'Consolas', monospace;
            }
            QTabBar::tab:selected { background-color: #141923; color: #ffaa00; font-weight: bold; }
            QFrame#HeaderCard { background-color: #10141d; border: 1px solid #1f2430; border-radius: 6px; }
            QPushButton { background-color: #1b2230; border: 1px solid #2b384e; border-radius: 4px; color: #ffffff; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #242f44; border-color: #ffaa00; }
            QLabel { color: #ffffff; font-family: 'Segoe UI', sans-serif; }
        """)

        self.central_container = QWidget()
        self.setCentralWidget(self.central_container)
        self.main_layout = QVBoxLayout(self.central_container)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(20, 15, 20, 15)

        status_text_layout = QVBoxLayout()
        system_title = QLabel("EXOSUIT INTEGRATED COGNITION MATRIX")
        system_title.setStyleSheet("font-family: 'Consolas', monospace; font-size: 15px; font-weight: bold; color: #ffffff;")

        self.status_badge = QLabel("STATUS: INITIALIZING SYSTEM ASSETS...")
        self.status_badge.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; color: #ffaa00; font-weight: bold;")

        status_text_layout.addWidget(system_title)
        status_text_layout.addWidget(self.status_badge)
        header_layout.addLayout(status_text_layout)
        header_layout.addStretch()

        self.launch_btn = QPushButton("ENGAGE AI CORE")
        self.launch_btn.setEnabled(False)
        self.launch_btn.setStyleSheet("background-color: #222225; border: 1px solid #444448; color: #66666d; padding: 10px 20px;")
        header_layout.addWidget(self.launch_btn)
        self.main_layout.addWidget(header_card)

        # Loading Panel: Shows up instantly with the window to provide visual feedback
        self.loading_panel = QFrame()
        self.loading_panel.setStyleSheet("background-color: #10141d; border: 1px solid #1f2430; border-radius: 4px;")
        load_layout = QVBoxLayout(self.loading_panel)
        load_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_msg = QLabel("SYNCHRONIZING EXOSUIT DATA ASSETS (READING LLM MATRIX FILES)...")
        self.loading_msg.setStyleSheet("font-family: 'Consolas', monospace; color: #ffaa00; font-size: 12px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedWidth(350)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")

        load_layout.addWidget(self.loading_msg, alignment=Qt.AlignmentFlag.AlignCenter)
        load_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.loading_panel, stretch=1)

    def _setup_system_tray(self):
        self.tray_icon = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(QIcon(str(self.tray_icon_path)), self)
        self.tray_icon.setToolTip("NMS Dynamic Suit Voice")
        tray_menu = QMenu(self)
        show_action = QAction("Show Control Deck", self)
        show_action.triggered.connect(self.show_window)
        quit_action = QAction("Close everything completely", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()

    def launch_background_config_loader(self):
        self.loader_thread = ConfigLoaderWorker()
        self.loader_thread.config_loaded_signal.connect(self.on_config_loading_complete)
        self.loader_thread.config_failed_signal.connect(
            self.on_config_loading_failed
        )
        self.loader_thread.finished.connect(self._finish_shutdown_if_requested)
        self.loader_thread.start()

    def on_config_loading_failed(self, error):
        if self._quit_requested:
            return
        self.loading_msg.setText(f"Configuration load failed: {error}")
        self.progress_bar.hide()
        self.status_badge.setText("STATUS: CONFIGURATION ERROR")
        self.status_badge.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px; "
            "color: #ff3333; font-weight: bold;"
        )
        QMessageBox.critical(
            self,
            "Configuration load failed",
            f"The control deck could not load its configuration:\n{error}",
        )

    def on_config_loading_complete(self, config_instance):
        if self._quit_requested:
            return
        self.config = config_instance

        # Clean up loading panel visual stubs
        self.main_layout.removeWidget(self.loading_panel)
        self.loading_panel.deleteLater()

        # Swap in the interactive tab matrix notebook
        self.main_layout.addWidget(self.notebook, stretch=1)

        button_frame = QWidget()
        btn_layout = QHBoxLayout(button_frame)
        btn_layout.setContentsMargins(0, 5, 0, 0)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        apply_btn = QPushButton("Apply Changes")
        apply_btn.clicked.connect(self.apply_preferences)
        save_close_btn = QPushButton("Save & Minimize")
        save_close_btn.clicked.connect(self.save_and_close)

        button_style = """
            QPushButton { background-color: #1b2230; border: 1px solid #2b384e; border-radius: 4px; color: #ffffff; padding: 8px 16px; min-width: 90px; }
            QPushButton:hover { background-color: #242f44; border-color: #ffaa00; }
        """
        cancel_btn.setStyleSheet(button_style)
        apply_btn.setStyleSheet(button_style)
        save_close_btn.setStyleSheet("background-color: #005588; border: 1px solid #00aaff; color: white; padding: 8px 16px; min-width: 90px;")

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(save_close_btn)
        self.main_layout.addWidget(button_frame)

        self.status_badge.setText("STATUS: OFFLINE (STANDBY MODE)")
        self.status_badge.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; color: #ff3333; font-weight: bold;")

        self.launch_btn.setEnabled(True)
        self.launch_btn.setStyleSheet("""
            QPushButton { background-color: #885500; border: 1px solid #ffaa00; color: #ffffff; font-size: 12px; padding: 10px 20px; }
            QPushButton:hover { background-color: #aa7700; }
        """)
        self.launch_btn.clicked.connect(self.toggle_engine_state)

        # Scan and load layout panels seamlessly now that self.config exists
        self.discover_and_mount_panels()

    def toggle_engine_state(self):
        if self._quit_requested:
            return

        if self.engine_thread is not None and self.engine_thread.isRunning():
            self.engine_thread.running = False
            self.engine_thread.stop_event.set()
            self.status_badge.setText("STATUS: STOPPING ENGINE...")
            self.launch_btn.setEnabled(False)
            return

        self._engine_error_message = None
        self.status_badge.setText("STATUS: STARTING ENGINE...")
        self.status_badge.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px; "
            "color: #ffaa00; font-weight: bold;"
        )
        self.launch_btn.setText("DISENGAGE AI CORE")
        self.launch_btn.setEnabled(True)
        self.launch_btn.setStyleSheet(
            "background-color: #551111; border: 1px solid #ff3333; "
            "color: white; font-size: 12px; padding: 10px 20px;"
        )
        self.engine_thread = ExosuitEngineThread(self.config)
        self.engine_thread.status_signal.connect(self._on_engine_status)
        self.engine_thread.engine_log_signal.connect(self._on_engine_error)
        self.engine_thread.finished.connect(self._on_engine_finished)
        self.engine_thread.start()

    def _on_engine_status(self, message, is_ready):
        if self._quit_requested:
            return
        color = "#00ff66" if is_ready else "#ffaa00"
        self.status_badge.setText(f"STATUS: {message.upper()}")
        self.status_badge.setStyleSheet(
            f"font-family: 'Consolas', monospace; font-size: 11px; "
            f"color: {color}; font-weight: bold;"
        )
        if self.tray_icon is not None:
            self.tray_icon.setToolTip(f"NMS Dynamic Suit Voice - {message}")

    def _on_engine_error(self, message):
        self._engine_error_message = message
        self.status_badge.setText("STATUS: ENGINE ERROR")
        self.status_badge.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px; "
            "color: #ff3333; font-weight: bold;"
        )
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "NMS Dynamic Suit Voice",
                message,
                QSystemTrayIcon.MessageIcon.Critical,
            )

    def _on_engine_finished(self):
        self.engine_thread = None
        if self._quit_requested:
            self._finish_shutdown_if_requested()
            return

        self.launch_btn.setEnabled(True)
        self.launch_btn.setText("ENGAGE AI CORE")
        self.launch_btn.setStyleSheet("""
            QPushButton { background-color: #885500; border: 1px solid #ffaa00; color: #ffffff; font-size: 12px; padding: 10px 20px; }
            QPushButton:hover { background-color: #aa7700; }
        """)
        if self._engine_error_message:
            self.status_badge.setText("STATUS: ENGINE ERROR")
            return
        self.status_badge.setText("STATUS: OFFLINE (STANDBY MODE)")
        self.status_badge.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 11px; "
            "color: #ff3333; font-weight: bold;"
        )

    def quit_application(self):
        self._quit_requested = True
        self.launch_btn.setEnabled(False)
        self.status_badge.setText("STATUS: SHUTTING DOWN...")
        if self.engine_thread is not None:
            self.engine_thread.running = False
            self.engine_thread.stop_event.set()
        self._finish_shutdown_if_requested()

    def _finish_shutdown_if_requested(self):
        if not self._quit_requested:
            return
        if self.loader_thread is not None and self.loader_thread.isRunning():
            return
        if self.engine_thread is not None and self.engine_thread.isRunning():
            return

        self._allow_close = True
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return
        if self.tray_icon is not None and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            if not self._tray_notice_shown:
                self.tray_icon.showMessage(
                    "NMS Dynamic Suit Voice",
                    "The control deck is still running in the system tray.",
                    QSystemTrayIcon.MessageIcon.Information,
                )
                self._tray_notice_shown = True
            return

        event.ignore()
        self.quit_application()

    def discover_and_mount_panels(self):
        panels_dir = Path(__file__).parent / "panels"
        if not panels_dir.exists():
            return

        scanned_files = sorted(list(panels_dir.glob("panel_*.py")))
        for file_path in scanned_files:
            module_name = file_path.stem
            try:
                imported_module = importlib.import_module(
                    f"interface.panels.{module_name}"
                )
                words = [w for w in module_name.split('_')[1:] if not w.isdigit()]
                class_name = "".join(w.capitalize() for w in words) + "Panel"
                panel_class = getattr(imported_module, class_name, None)

                if panel_class:
                    display_title = " ".join(w.capitalize() for w in words)
                    title_overrides = {"Profile": "User Profile", "Audio": "Audio Modifiers"}
                    display_title = title_overrides.get(display_title, display_title)

                    panel_instance = panel_class(self.config)
                    self.notebook.addTab(panel_instance, display_title)
                    if hasattr(panel_instance, "settings_requested"):
                        panel_instance.settings_requested.connect(
                            self._open_debug_settings
                        )
            except Exception as load_err:
                message = debug_error_message(
                    load_err, f"Loading interface panel {module_name}"
                )
                print(f"[PANEL FAULT] {message}")

    def _open_debug_settings(self, target):
        panel_name, _, section = target.partition("/")
        for index in range(self.notebook.count()):
            if self.notebook.tabText(index).casefold() != panel_name.casefold():
                continue
            panel = self.notebook.widget(index)
            self.notebook.setCurrentIndex(index)
            if section and hasattr(panel, "request_settings"):
                panel.request_settings(section)
            return
        QMessageBox.warning(
            self,
            "Settings unavailable",
            f"The recommended settings panel is not available: {panel_name}.",
        )

    def gather_all_panel_data(self):
        for i in range(self.notebook.count()):
            panel_widget = self.notebook.widget(i)
            if panel_widget is not None and hasattr(panel_widget, "gather_settings"):
                getattr(panel_widget, "gather_settings")()

    def apply_preferences(self):
        if self.config is None:
            QMessageBox.warning(self, "System Busy", "Configuration layers are still initializing. Please wait.")
            return

        try:
            self.gather_all_panel_data()
            self._save_configuration_files()
            QMessageBox.information(
                self,
                "Applied",
                "Preferences were saved to the configuration files. "
                "Restart the application to apply path changes.",
            )
        except Exception as e:
            message = debug_error_message(e, "Saving application preferences")
            QMessageBox.critical(
                self, "Error", f"Failed to commit settings to file system maps:\n{message}"
            )

    def save_and_close(self):
        if self.config is None:
            self.close()
            return

        try:
            self.gather_all_panel_data()
            self._save_configuration_files()
            QMessageBox.information(
                self,
                "Success",
                "Configurations saved. The control deck will minimize to the system tray.",
            )
            self.close()
        except Exception as e:
            message = debug_error_message(e, "Saving preferences before closing")
            QMessageBox.critical(self, "Error", f"Failed to finalize files:\n{message}")

    def _save_configuration_files(self):
        config = self.config
        if config is None:
            raise RuntimeError("Configuration is not loaded.")

        config_directory = Path(__file__).parent.parent / "config"
        files = (
            (
                config_directory / "environment_config.json",
                config.environment,
            ),
            (
                config_directory / "user_customization.json",
                config.user_customization,
            ),
        )
        for target_path, data in files:
            write_json_atomic(target_path, data)

def main():
    app = QApplication(sys.argv)
    install_exception_hooks()
    app.setQuitOnLastWindowClosed(False)
    instance_key = hashlib.sha256(str(project_root).encode("utf-8")).hexdigest()[:12]
    lock_path = Path(tempfile.gettempdir()) / f"nms_dynamic_suit_voice_{instance_key}.lock"
    instance_lock = QLockFile(str(lock_path))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(0):
        return
    window = ControlDeckDashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
