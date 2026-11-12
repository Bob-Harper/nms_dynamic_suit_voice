# interface/panels/panel_2_updates.py
import sys
import json
import shutil
import subprocess
import threading
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from interface.panels.widgets.shared import build_card

class UpdatesPanel(QWidget):
    # Thread-safe pipeline signaling lanes to update status text from background threads
    status_signal = Signal(str)
    action_complete_signal = Signal(bool, str)

    def __init__(self, config):
        super().__init__()
        # Single point of truth passed by reference. No pipeline imports allowed.
        self.config = config

        # Force-align the execution context to look at the true root project directory
        self.project_root = Path(__file__).resolve().parents[2]
        self._tracked_repository = False

        # Connect signaling channels across background loops
        self.status_signal.connect(self._update_status_label)
        self.action_complete_signal.connect(self._on_action_finished)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Leverage single-source shared style factory block
        card, card_layout = build_card("EXOSUIT ECOSYSTEM COMPLIANCE REGISTRY")

        project = self.config.environment.get("project", {})
        version_label = QLabel(f"Installed Version Track: v{project.get('version', 'Unknown')}")
        version_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; border: none;")
        card_layout.addWidget(version_label)

        # DIAGNOSTIC LOGGER LABEL: Plain-text state tracker
        self.status_reporter = QLabel("Ecosystem Status: Standing By...")
        self.status_reporter.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px; color: #ffaa00; border: none; padding: 4px 0;")
        card_layout.addWidget(self.status_reporter)

        # Top Button Row: Maintenance Actions
        top_button_row = QHBoxLayout()
        top_button_row.setSpacing(10)

        btn_style = """
            QPushButton {
                background-color: #1b2230; border: 1px solid #2b384e; color: white;
                padding: 10px 16px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px;
            }
            QPushButton:hover { background-color: #242f44; border-color: #ffaa00; }
            QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }
        """

        self.check_button = QPushButton("CHECK FOR UPDATES")
        self.check_button.setStyleSheet(btn_style)
        self.check_button.clicked.connect(self._trigger_async_check)

        self.convert_button = QPushButton("CONVERT THIS INSTALL TO GIT")
        self.convert_button.setStyleSheet(btn_style)
        self.convert_button.clicked.connect(self._trigger_async_conversion)

        top_button_row.addWidget(self.check_button)
        top_button_row.addWidget(self.convert_button)
        top_button_row.addStretch()
        card_layout.addLayout(top_button_row)

        # Bottom Button Row: Deployment Actions
        bottom_button_row = QHBoxLayout()
        bottom_button_row.setSpacing(10)

        self.pull_button = QPushButton("PULL AVAILABLE UPDATES")
        self.pull_button.setStyleSheet("""
            QPushButton {
                background-color: #004477; border: 1px solid #0088cc; color: white;
                padding: 10px 16px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px;
            }
            QPushButton:hover { background-color: #005588; border-color: #ffaa00; }
            QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }
        """)
        self.pull_button.clicked.connect(self._trigger_async_pull)
        bottom_button_row.addWidget(self.pull_button)
        bottom_button_row.addStretch()
        card_layout.addLayout(bottom_button_row)

        note = QLabel(
            "Notice: Git updates are available only after this installation is converted "
            "to a tracked repository loop. Reconciling version profiles ensures local "
            "configuration changes are preserved when synchronizing directories."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5c6773; font-size: 11px; border: none; padding-top: 5px;")
        card_layout.addWidget(note)

        layout.addWidget(card)
        layout.addStretch()

        # Execute initial verification check silently on layout instantiation
        self._refresh_install_state()

    @Slot(str)
    def _update_status_label(self, message_text):
        self.status_reporter.setText(f"Ecosystem Status: {message_text}")

    @Slot(bool, str)
    def _on_action_finished(self, success, alert_msg):
        self._refresh_install_state()
        if alert_msg:
            if success:
                QMessageBox.information(self, "Registry Alert", alert_msg)
            else:
                QMessageBox.warning(self, "Pipeline Exception", alert_msg)

    def _refresh_install_state(self):
        """Checks the workspace directory structure to toggle correct button activity blocks."""
        git_dir = self.project_root / ".git"
        if git_dir.exists():
            self._tracked_repository = True
            self.status_reporter.setText("Ecosystem Status: This installation is actively tracked by Git.")
            self.convert_button.setEnabled(False)
            self.pull_button.setEnabled(True)
        else:
            self._tracked_repository = False
            self.status_reporter.setText("Ecosystem Status: ZIP / extracted installation archive (untracked).")
            self.convert_button.setEnabled(True)
            self.pull_button.setEnabled(False)

        self.check_button.setEnabled(True)

    def _trigger_async_check(self):
        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)
        self.status_reporter.setText("Contacting remote forge registry variables...")
        threading.Thread(target=self._worker_check_updates, daemon=True).start()

    def _worker_check_updates(self):
        try:
            updates = self.config.environment.get("updates", {})
            repo_url = updates.get("repository_url", "https://github.com/Bob-Harper/nms_dynamic_suit_voice")
            branch = updates.get("branch", "main")
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            remote_line = subprocess.run(
                ["git", "ls-remote", repo_url, f"refs/heads/{branch}"],
                capture_output=True, text=True, timeout=20, creationflags=cmd_flags
            ).stdout.strip()

            if not remote_line:
                self.status_signal.emit(f"Failed to resolve branch target reference '{branch}'.")
                self.action_complete_signal.emit(False, "")
                return

            remote_commit = remote_line.split()[0]
            git_dir = self.project_root / ".git"

            if git_dir.exists():
                local_commit = subprocess.run(
                    ["git", "-C", str(self.project_root), "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=10, creationflags=cmd_flags
                ).stdout.strip()

                if local_commit == remote_commit:
                    self.status_signal.emit(f"Mod files are completely up to date ({remote_commit[:8]})")
                else:
                    self.status_signal.emit(f"Update available on registry ({local_commit[:8]} -> {remote_commit[:8]})")
            else:
                self.status_signal.emit("Untracked workspace archive. Click 'CONVERT THIS INSTALL TO GIT' to enable easy updating.")
        except Exception as e:
            self.status_signal.emit(f"Network verification loop fault: {e}")
        finally:
            self.action_complete_signal.emit(True, "")

    def _trigger_async_conversion(self):
        updates = self.config.environment.get("updates", {})
        repository_url = updates.get("repository_url", "https://github.com/Bob-Harper/nms_dynamic_suit_voice")
        branch = updates.get("branch", "main")

        answer = QMessageBox.question(
            self, "Convert installation to Git",
            "This adds Git tracking parameters to the current installation folder layout without replacing existing mod files.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)
        self.status_reporter.setText("Initializing local Git configuration tables...")

        threading.Thread(target=self._worker_convert_to_git, args=(repository_url, branch), daemon=True).start()

    def _worker_convert_to_git(self, repository_url, branch):
        try:
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.status_signal.emit("Initializing local .git folder architectures...")
            subprocess.run(["git", "init"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(f"Binding symbolic reference head to target branch: '{branch}'...")
            subprocess.run(["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(f"Mapping remote deployment origin to: {repository_url}...")
            subprocess.run(["git", "remote", "add", "origin", repository_url], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit("Fetching upstream repository files snapshots...")
            subprocess.run(["git", "fetch", "origin", branch], cwd=str(self.project_root), capture_output=True, check=True, timeout=120, creationflags=cmd_flags)

            self.status_signal.emit("Reconciling directory index tables...")
            subprocess.run(["git", "reset", "--mixed", f"origin/{branch}"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            subprocess.run(["git", "branch", f"--set-upstream-to=origin/{branch}", branch], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit("Update Tracking now active. Evaluation pass complete.")
            self.action_complete_signal.emit(True, "This installation folder is now actively tracked by Git. Updates can now be directly requested and pulled.")

        except Exception as e:
            self.status_signal.emit("Conversion pipeline aborted.")
            self.action_complete_signal.emit(False, f"Git tracking construction failed:\n{e}")

    def _trigger_async_pull(self):

        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)

        self.status_reporter.setText("Synchronizing files transport streams over secure transport...")
        threading.Thread(target=self._worker_pull_updates, daemon=True).start()

    def _worker_pull_updates(self):
        try:
            updates = self.config.environment.get("updates", {})
            branch = updates.get("branch", "main")
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.status_signal.emit("Fetching latest mod iterations from forge registry...")
            subprocess.run(["git", "-C", str(self.project_root), "fetch", "origin"], capture_output=True, check=True, timeout=60, creationflags=cmd_flags)

            self.status_signal.emit("Executing fast-forward directory alignment merge...")
            subprocess.run(["git", "-C", str(self.project_root), "merge", "--ff-only", f"origin/{branch}"], capture_output=True, check=True, timeout=60, creationflags=cmd_flags)

            self.status_signal.emit("Synchronized! RESTART APPLICATION TO COMPLETE THE UPDATE.")
            self.action_complete_signal.emit(True, "Mod iteration pulled successfully! Please restart the control deck window interface to execute the newly deployed changes.")

        except Exception as e:
            self.status_signal.emit("Sync operation interrupted.")
            self.action_complete_signal.emit(False, f"Git synchronizer aborted the update:\n{e}")

    def gather_settings(self):
        """Pass-through validation handle to prevent system interface crashes during preference saves."""
        pass