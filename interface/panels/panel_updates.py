# interface/panels/panel_2_updates.py
import shutil
import sys
import subprocess
import threading
from pathlib import Path
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from interface.panels.widgets.shared import build_card
from pipeline.localization import t


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

        card, card_layout = build_card(t("UI_PANEL_UPDATES_001"))

        self.version_label = QLabel(t("UI_PANEL_UPDATES_002"))
        self.version_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; border: none;")
        card_layout.addWidget(self.version_label)

        self.status_reporter = QLabel(t("UI_PANEL_UPDATES_003", status=t("UI_PANEL_UPDATES_004")))
        self.status_reporter.setWordWrap(True)
        self.status_reporter.setOpenExternalLinks(True)
        self.status_reporter.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px; color: #ffaa00; border: none; padding: 4px 0;")
        card_layout.addWidget(self.status_reporter)

        # Top Button Row: Maintenance Actions
        top_button_row = QHBoxLayout()
        top_button_row.setSpacing(10)

        btn_style = (
            "QPushButton {"
            " background-color: #1b2230; border: 1px solid #2b384e; color: white;"
            " padding: 10px 16px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px;"
            "}"
            "QPushButton:hover { background-color: #242f44; border-color: #ffaa00; }"
            "QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }"
        )

        self.check_button = QPushButton(t("UI_PANEL_UPDATES_005"))
        self.check_button.setStyleSheet(btn_style)
        self.check_button.clicked.connect(self._trigger_async_check)

        self.convert_button = QPushButton(t("UI_PANEL_UPDATES_006"))
        self.convert_button.setStyleSheet(btn_style)
        self.convert_button.clicked.connect(self._trigger_async_conversion)

        top_button_row.addWidget(self.check_button)
        top_button_row.addWidget(self.convert_button)
        top_button_row.addStretch()
        card_layout.addLayout(top_button_row)

        # Bottom Button Row: Deployment Actions
        bottom_button_row = QHBoxLayout()
        bottom_button_row.setSpacing(10)

        self.pull_button = QPushButton(t("UI_PANEL_UPDATES_007"))
        self.pull_button.setStyleSheet(
            "QPushButton {"
            " background-color: #004477; border: 1px solid #0088cc; color: white;"
            " padding: 10px 16px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px;"
            "}"
            "QPushButton:hover { background-color: #005588; border-color: #ffaa00; }"
            "QPushButton:disabled { background-color: #181d26; border-color: #222b3c; color: #4b5668; }"
        )
        self.pull_button.clicked.connect(self._trigger_async_pull)
        bottom_button_row.addWidget(self.pull_button)
        bottom_button_row.addStretch()
        card_layout.addLayout(bottom_button_row)

        note = QLabel(t("UI_PANEL_UPDATES_008"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #5c6773; font-size: 11px; border: none; padding-top: 5px;")
        card_layout.addWidget(note)

        layout.addWidget(card)
        layout.addStretch()

        self._refresh_install_state(preserve_status=False)

    def _get_local_commit_sha(self) -> str:
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            return t("UI_PANEL_UPDATES_009")
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
        return t("UI_PANEL_UPDATES_010")

    def _update_version_header(self):
        project = self.config.environment.get("project", {})
        ver = project.get("version", t("UI_PANEL_UPDATES_010"))
        local_sha = self._get_local_commit_sha()
        self.version_label.setText(t("UI_PANEL_UPDATES_011", version=ver, sha=local_sha))

    @Slot(str, str)
    def _update_status_label(self, message_text, color_hex="#ffaa00"):
        self.status_reporter.setStyleSheet(
            f"font-family: 'Consolas', monospace; font-size: 12px; color: {color_hex}; border: none; padding: 4px 0;"
        )
        self.status_reporter.setText(t("UI_PANEL_UPDATES_003", status=message_text))

    @Slot(bool, str, bool)
    def _on_action_finished(self, success, alert_msg, preserve_status):
        self._refresh_install_state(preserve_status=preserve_status)
        if alert_msg:
            if success:
                QMessageBox.information(self, t("UI_PANEL_UPDATES_012"), alert_msg)
            else:
                QMessageBox.warning(self, t("UI_PANEL_UPDATES_013"), alert_msg)

    def _refresh_install_state(self, preserve_status: bool = False):
        self._update_version_header()

        if shutil.which("git") is None:
            self._tracked_repository = False
            self.check_button.setEnabled(False)
            self.convert_button.setEnabled(False)
            self.pull_button.setEnabled(False)
            if not preserve_status:
                self._update_status_label(t("UI_PANEL_UPDATES_014"), "#ff3333")
            return

        git_dir = self.project_root / ".git"
        if git_dir.exists():
            self._tracked_repository = True
            if not preserve_status:
                self._update_status_label(
                    t("UI_PANEL_UPDATES_015", check_btn=t("UI_PANEL_UPDATES_005")),
                    "#ffaa00",
                )
            self.convert_button.setEnabled(False)
            self.pull_button.setEnabled(True)
        else:
            self._tracked_repository = False
            if not preserve_status:
                self._update_status_label(t("UI_PANEL_UPDATES_016"), "#ffaa00")
            self.convert_button.setEnabled(True)
            self.pull_button.setEnabled(False)

        self.check_button.setEnabled(True)

    def _trigger_async_check(self):
        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)
        self._update_status_label(t("UI_PANEL_UPDATES_017"), "#00aaff")
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
                    err = fetch_res.stderr.strip() or t("UI_PANEL_UPDATES_018")
                    self.status_signal.emit(t("UI_PANEL_UPDATES_019", error=err), "#ff3333")
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
                    self.status_signal.emit(t("UI_PANEL_UPDATES_020", sha=local_sha), "#00ff66")
                elif behind_count > 0:
                    self.status_signal.emit(
                        t("UI_PANEL_UPDATES_021", count=behind_count, local_sha=local_sha, remote_sha=remote_sha),
                        "#ffaa00",
                    )
                else:
                    self.status_signal.emit(
                        t("UI_PANEL_UPDATES_022", branch=branch, local_sha=local_sha, remote_sha=remote_sha),
                        "#ffaa00",
                    )
                self.action_complete_signal.emit(True, "", True)
            else:
                remote_line = subprocess.run(
                    ["git", "ls-remote", repo_url, f"refs/heads/{branch}"],
                    capture_output=True, text=True, timeout=20, creationflags=cmd_flags
                ).stdout.strip()

                if not remote_line:
                    self.status_signal.emit(t("UI_PANEL_UPDATES_023", branch=branch), "#ff3333")
                else:
                    remote_sha = remote_line.split()[:7]
                    self.status_signal.emit(
                        t("UI_PANEL_UPDATES_024", remote_sha=remote_sha, convert_btn=t("UI_PANEL_UPDATES_006")),
                        "#ffaa00",
                    )
                self.action_complete_signal.emit(True, "", True)

        except Exception as e:
            self.status_signal.emit(t("UI_PANEL_UPDATES_025", error=e), "#ff3333")
            self.action_complete_signal.emit(False, "", True)

    def _trigger_async_conversion(self):
        updates = self.config.environment.get("updates", {})
        repository_url = updates.get("repository_url")
        branch = updates.get("branch", "main")

        answer = QMessageBox.question(
            self,
            t("UI_PANEL_UPDATES_026"),
            t("UI_PANEL_UPDATES_027"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)
        self._update_status_label(t("UI_PANEL_UPDATES_028"), "#00aaff")

        threading.Thread(target=self._worker_convert_to_git, args=(repository_url, branch), daemon=True).start()

    def _worker_convert_to_git(self, repository_url, branch):
        try:
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.status_signal.emit(t("UI_PANEL_UPDATES_029"), "#00aaff")
            subprocess.run(["git", "init"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(t("UI_PANEL_UPDATES_030", branch=branch), "#00aaff")
            subprocess.run(["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(t("UI_PANEL_UPDATES_031", url=repository_url), "#00aaff")
            subprocess.run(["git", "remote", "add", "origin", repository_url], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            self.status_signal.emit(t("UI_PANEL_UPDATES_032"), "#00aaff")
            subprocess.run(["git", "fetch", "origin", branch], cwd=str(self.project_root), capture_output=True, check=True, timeout=120, creationflags=cmd_flags)

            self.status_signal.emit(t("UI_PANEL_UPDATES_033"), "#00aaff")
            subprocess.run(["git", "reset", "--mixed", f"origin/{branch}"], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            subprocess.run(["git", "branch", f"--set-upstream-to=origin/{branch}", branch], cwd=str(self.project_root), capture_output=True, check=True, creationflags=cmd_flags)

            local_sha = self._get_local_commit_sha()
            self.status_signal.emit(t("UI_PANEL_UPDATES_034", sha=local_sha), "#00ff66")
            self.action_complete_signal.emit(True, t("UI_PANEL_UPDATES_035"), True)

        except Exception as e:
            self.status_signal.emit(t("UI_PANEL_UPDATES_036"), "#ff3333")
            self.action_complete_signal.emit(False, t("UI_PANEL_UPDATES_037", error=e), True)

    def _trigger_async_pull(self):
        self.check_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.pull_button.setEnabled(False)

        self._update_status_label(t("UI_PANEL_UPDATES_038"), "#00aaff")
        threading.Thread(target=self._worker_pull_updates, daemon=True).start()

    def _worker_pull_updates(self):
        try:
            updates = self.config.environment.get("updates", {})
            branch = updates.get("branch", "main")
            cmd_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.status_signal.emit(t("UI_PANEL_UPDATES_039"), "#00aaff")
            subprocess.run(["git", "-C", str(self.project_root), "fetch", "origin"], capture_output=True, check=True, timeout=60, creationflags=cmd_flags)

            self.status_signal.emit(t("UI_PANEL_UPDATES_040"), "#00aaff")
            subprocess.run(["git", "-C", str(self.project_root), "merge", "--ff-only", f"origin/{branch}"], capture_output=True, check=True, timeout=60, creationflags=cmd_flags)

            self.status_signal.emit(t("UI_PANEL_UPDATES_041"), "#00aaff")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True, text=True, timeout=120, creationflags=cmd_flags
            )

            req_file = self.project_root / "requirements.txt"
            if req_file.exists():
                self.status_signal.emit(t("UI_PANEL_UPDATES_042"), "#00aaff")
                pip_res = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=300, creationflags=cmd_flags
                )
                if pip_res.returncode != 0:
                    err = pip_res.stderr.strip() or pip_res.stdout.strip() or t("UI_PANEL_UPDATES_043")
                    self.status_signal.emit(t("UI_PANEL_UPDATES_044"), "#ff3333")
                    self.action_complete_signal.emit(
                        False,
                        t("UI_PANEL_UPDATES_045", error=err),
                        True,
                    )
                    return

            local_sha = self._get_local_commit_sha()
            self.status_signal.emit(t("UI_PANEL_UPDATES_046", sha=local_sha), "#00ff66")
            self.action_complete_signal.emit(True, t("UI_PANEL_UPDATES_047"), True)

        except Exception as e:
            self.status_signal.emit(t("UI_PANEL_UPDATES_048"), "#ff3333")
            self.action_complete_signal.emit(False, t("UI_PANEL_UPDATES_049", error=e), True)

    def gather_settings(self):
        pass
