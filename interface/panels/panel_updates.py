# interface/panels/panel_2_updates.py
import sys
import subprocess
import threading
from pathlib import Path
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from interface.panels.widgets.shared import build_card


class UpdatesPanel(QWidget):
    status_signal = Signal(str, str)  # (message_text, hex_color)
    action_complete_signal = Signal(bool, str, bool)  # (success, alert_msg, preserve_status)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.project_root = Path(__file__).resolve().parents[2]
        self._tracked_repository = False

        self.status_signal.connect(self._update_status_label)
        self.action_complete_signal.connect(self._on_action_finished)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        card, card_layout = build_card("EXOSUIT ECOSYSTEM COMPLIANCE REGISTRY")

        self.version_label = QLabel("Installed Version: Loading...")
        self.version_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; border: none;")
        card_layout.addWidget(self.version_label)

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
            "to a tracked repository. Existing local configuration files are preserved when pulling updates."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5c6773; font-size: 11px; border: none; padding-top: 5px;")
        card_layout.addWidget(note)

        layout.addWidget(card)
        layout.addStretch()

        self._refresh_install_state(preserve_status=False)

    def _get_local_commit_sha(self) -> str:
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            return "Untracked Archive"
        try:
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            res = subprocess.run(
                ["git", "-C", str(self.project_root), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=10, creationflags=cmd_flags
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "Unknown"

    def _update_version_header(self):
        project = self.config.environment.get("project", {})
        ver = project.get("version", "Unknown")
        local_sha = self._get_local_commit_sha()
        self.version_label.setText(f"Installed Version: v{ver}  |  Local Commit: {local_sha}")

    @Slot(str, str)
    def _update_status_label(self, message_text, color_hex="#ffaa00"):
        self.status_reporter.setStyleSheet(
            f"font-family: 'Consolas', monospace; font-size: 12px; color: {color_hex}; border: none; padding: 4px 0;"
        )
        self.status_reporter.setText(f"Ecosystem Status: {message_text}")

    @Slot(bool, str, bool)
    def _on_action_finished(self, success, alert_msg, preserve_status):
        self._refresh_install_state(preserve_status=preserve_status)
        if alert_msg:
            if success:
                QMessageBox.information(self, "Registry Alert", alert_msg)
            else:
                QMessageBox.warning(self, "Pipeline Exception", alert_msg)

    def _refresh_install_state(self, preserve_status: bool = False):
        self._update_version_header()
        git_dir = self.project_root / ".git"
        if git_dir.exists():
            self._tracked_repository = True
            if not preserve_status:
                self._update_status_label("Git Tracked (Click 'CHECK FOR UPDATES' to compare with GitHub)", "#ffaa00")
            self.convert_button.setEnabled(False)
            self.pull_button.setEnabled(True)
        else:
            self._tracked_repository = False
            if not preserve_status:
                self._update_status_label("ZIP / extracted installation archive (untracked).", "#ffaa00")
            self.convert_button.setEnabled(True)
            self.pull_button.setEnabled(False)

        self.check_button.setEnabled(True)

    def _trigger_async_check(self):
        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)
        self._update_status_label("Fetching remote repository state...", "#00aaff")
        threading.Thread(target=self._worker_check_updates, daemon=True).start()

    def _worker_check_updates(self):
        try:
            updates = self.config.environment.get("updates", {})
            repo_url = updates.get("repository_url")
            branch = updates.get("branch", "main")
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            git_dir = self.project_root / ".git"

            if git_dir.exists():
                fetch_res = subprocess.run(
                    ["git", "-C", str(self.project_root), "fetch", "origin", branch],
                    capture_output=True, text=True, timeout=25, creationflags=cmd_flags
                )
                if fetch_res.returncode != 0:
                    err = fetch_res.stderr.strip() or "Failed to reach remote origin."
                    self.status_signal.emit(f"Update check failed: {err}", "#ff3333")
                    self.action_complete_signal.emit(False, "", True)
                    return

                local_sha = subprocess.run(
                    ["git", "-C", str(self.project_root), "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=10, creationflags=cmd_flags
                ).stdout.strip()

                remote_sha = subprocess.run(
                    ["git", "-C", str(self.project_root), "rev-parse", "--short", f"origin/{branch}"],
                    capture_output=True, text=True, timeout=10, creationflags=cmd_flags
                ).stdout.strip()

                behind_str = subprocess.run(
                    ["git", "-C", str(self.project_root), "rev-list", "--count", f"HEAD..origin/{branch}"],
                    capture_output=True, text=True, timeout=10, creationflags=cmd_flags
                ).stdout.strip()

                behind_count = int(behind_str) if behind_str.isdigit() else 0

                if behind_count == 0 and local_sha == remote_sha:
                    self.status_signal.emit(f"YOU ARE UP TO DATE (Commit: {local_sha})", "#00ff66")
                elif behind_count > 0:
                    self.status_signal.emit(
                        f"UPDATE AVAILABLE — {behind_count} commit(s) behind ({local_sha} -> {remote_sha})",
                        "#ffaa00"
                    )
                else:
                    self.status_signal.emit(
                        f"Local branch differs from origin/{branch} (Local: {local_sha} | Remote: {remote_sha})",
                        "#ffaa00"
                    )
                self.action_complete_signal.emit(True, "", True)
            else:
                remote_line = subprocess.run(
                    ["git", "ls-remote", repo_url, f"refs/heads/{branch}"],
                    capture_output=True, text=True, timeout=20, creationflags=cmd_flags
                ).stdout.strip()

                if not remote_line:
                    self.status_signal.emit(f"Failed to resolve remote branch '{branch}'.", "#ff3333")
                else:
                    remote_sha = remote_line.split()[:7]
                    self.status_signal.emit(
                        f"Untracked ZIP archive (Latest remote commit: {remote_sha}). Click 'CONVERT THIS INSTALL TO GIT' to enable updates.",
                        "#ffaa00"
                    )
                self.action_complete_signal.emit(True, "", True)

        except Exception as e:
            self.status_signal.emit(f"Update check fault: {e}", "#ff3333")
            self.action_complete_signal.emit(False, "", True)

    def _trigger_async_conversion(self):
        updates = self.config.environment.get("updates", {})
        repository_url = updates.get("repository_url")
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
        self._update_status_label("Initializing local Git configuration...", "#00aaff")

        threading.Thread(target=self._worker_convert_to_git, args=(repository_url, branch), daemon=True).start()

    def _worker_convert_to_git(self, repository_url, branch):
        try:
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.status_signal.emit("Initializing local .git folder...", "#00aaff")
            subprocess.run(["git", "init"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(f"Binding HEAD to branch '{branch}'...", "#00aaff")
            subprocess.run(["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(f"Setting remote origin to {repository_url}...", "#00aaff")
            subprocess.run(["git", "remote", "add", "origin", repository_url], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit("Fetching upstream repository files...", "#00aaff")
            subprocess.run(["git", "fetch", "origin", branch], cwd=str(self.project_root), capture_output=True, check=True, timeout=120, creationflags=cmd_flags)

            self.status_signal.emit("Aligning directory index...", "#00aaff")
            subprocess.run(["git", "reset", "--mixed", f"origin/{branch}"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            subprocess.run(["git", "branch", f"--set-upstream-to=origin/{branch}", branch], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            local_sha = self._get_local_commit_sha()
            self.status_signal.emit(f"Git tracking active — YOU ARE UP TO DATE (Commit: {local_sha})", "#00ff66")
            self.action_complete_signal.emit(True, "This installation folder is now actively tracked by Git. Updates can now be directly requested and pulled.", True)

        except Exception as e:
            self.status_signal.emit("Conversion pipeline aborted.", "#ff3333")
            self.action_complete_signal.emit(False, f"Git tracking construction failed:\n{e}", True)

    def _trigger_async_pull(self):
        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)

        self._update_status_label("Fetching updates from remote repository...", "#00aaff")
        threading.Thread(target=self._worker_pull_updates, daemon=True).start()

    def _worker_pull_updates(self):
        try:
            updates = self.config.environment.get("updates", {})
            branch = updates.get("branch", "main")
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.status_signal.emit("Fetching latest commits from origin...", "#00aaff")
            subprocess.run(["git", "-C", str(self.project_root), "fetch", "origin"], capture_output=True, check=True, timeout=60, creationflags=cmd_flags)

            self.status_signal.emit("Applying fast-forward update...", "#00aaff")
            subprocess.run(["git", "-C", str(self.project_root), "merge", "--ff-only", f"origin/{branch}"], capture_output=True, check=True, timeout=60, creationflags=cmd_flags)

            local_sha = self._get_local_commit_sha()
            self.status_signal.emit(f"Synchronized to {local_sha}! RESTART APPLICATION TO APPLY CHANGES.", "#00ff66")
            self.action_complete_signal.emit(True, "Updates pulled successfully! Please restart the control deck to run the updated code.", True)

        except Exception as e:
            self.status_signal.emit("Sync operation interrupted (check for local file modifications).", "#ff3333")
            self.action_complete_signal.emit(False, f"Git update aborted:\n{e}", True)

    def gather_settings(self):
        pass
