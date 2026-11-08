import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interface.panels.widgets.buildcard import build_card
from interface.panels.widgets.config_io import write_json_atomic


class UpdateManagementWidget(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.project_root = Path(__file__).resolve().parents[3]
        self._tracked_repository = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        card, card_layout = build_card("PROJECT UPDATE MANAGEMENT")

        project = self.config.environment.get("project", {})
        self.version_label = QLabel(
            f"Installed version: {project.get('version', 'Unknown')}"
        )
        self.repository_status = QLabel("Repository status: Not checked")
        self.repository_status.setWordWrap(True)

        updates = self.config.environment.get("updates", {})

        self.updates_enabled = QCheckBox("Enable update checks and update actions")
        self.updates_enabled.setChecked(bool(updates.get("enabled", False)))

        card_layout.addWidget(self.version_label)
        card_layout.addWidget(self.repository_status)
        card_layout.addWidget(self.updates_enabled)
        card_layout.addWidget(QLabel("Git repository URL"))
        self.repository_edit = QLineEdit(str(updates.get("repository_url", "")))
        card_layout.addWidget(self.repository_edit)
        card_layout.addWidget(QLabel("Branch"))
        self.branch_edit = QLineEdit(str(updates.get("branch", "")))
        card_layout.addWidget(self.branch_edit)

        button_row = QHBoxLayout()
        self.check_button = QPushButton("CHECK FOR UPDATES")
        self.convert_button = QPushButton("CONVERT THIS INSTALL TO GIT")
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.convert_button)
        card_layout.addLayout(button_row)

        self.pull_button = QPushButton("PULL AVAILABLE UPDATES")
        self.zip_button = QPushButton("DOWNLOAD ZIP INSTEAD")
        card_layout.addWidget(self.pull_button)
        card_layout.addWidget(self.zip_button)

        note = QLabel(
            "Git updates are available only after this installation is converted "
            "to a tracked repository. ZIP downloads do not change installed files; "
            "extract the ZIP over the installation and run "
            "'py -3.11 installer.py' from the project folder again."
        )
        note.setWordWrap(True)
        card_layout.addWidget(note)

        self.check_button.clicked.connect(self._check_updates)
        self.convert_button.clicked.connect(self._convert_to_git)
        self.pull_button.clicked.connect(self._pull_updates)
        self.zip_button.clicked.connect(self._download_zip)
        self.updates_enabled.toggled.connect(self._set_actions_enabled)
        self._set_actions_enabled(self.updates_enabled.isChecked())
        self._refresh_install_state()

        layout.addWidget(card)
        layout.addStretch()

    def _set_actions_enabled(self, enabled):
        for button in (self.check_button, self.pull_button, self.zip_button):
            button.setEnabled(enabled)
        self.convert_button.setEnabled(enabled and not self._tracked_repository)
        self.repository_edit.setEnabled(enabled)
        self.branch_edit.setEnabled(enabled)

    def _repository_and_branch(self):
        repository_url = self.repository_edit.text().strip()
        branch = self.branch_edit.text().strip()
        if not repository_url:
            raise ValueError("Enter a Git repository URL.")
        if not (
            repository_url.startswith(("https://", "ssh://"))
            or re.match(r"^git@[\w.-]+:", repository_url)
        ):
            raise ValueError("Use an HTTPS or SSH Git repository URL.")
        if not branch:
            raise ValueError("Enter a branch name.")
        if (
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch) is None
            or any(part in ("", ".", "..") for part in branch.split("/"))
            or branch.endswith((".", "/"))
            or branch.endswith(".lock")
            or "@{" in branch
        ):
            raise ValueError(f"Invalid Git branch name: {branch}")
        return repository_url, branch

    def _run_git(self, *args, timeout=120):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_root), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                "Git is not installed or is not available on PATH."
            ) from error
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(detail or f"Git command failed: {' '.join(args)}")
        return result.stdout.strip()

    def _is_git_repository(self):
        try:
            top_level = Path(
                self._run_git("rev-parse", "--show-toplevel")
            ).resolve()
            return top_level == self.project_root.resolve()
        except RuntimeError as error:
            if "not a git repository" in str(error).lower():
                return False
            raise

    def _refresh_install_state(self):
        try:
            if self._is_git_repository():
                self._tracked_repository = True
                self.repository_status.setText(
                    "Repository status: This installation is tracked by Git."
                )
            else:
                self._tracked_repository = False
                self.repository_status.setText(
                    "Repository status: ZIP/extracted install (not tracked)."
                )
            self._set_actions_enabled(self.updates_enabled.isChecked())
        except RuntimeError as error:
            self.repository_status.setText(f"Repository status check failed: {error}")

    def _matching_version_tag(self, repository_url):
        version = str(
            self.config.environment.get("project", {}).get("version", "")
        ).strip()
        if not version:
            return None

        for tag in (f"v{version}", version):
            try:
                result = subprocess.run(
                    [
                        "git",
                        "ls-remote",
                        "--tags",
                        repository_url,
                        f"refs/tags/{tag}",
                        f"refs/tags/{tag}^{{}}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise RuntimeError(
                    f"Could not check the remote release tag {tag}: {error}"
                ) from error
            if result.stdout.strip():
                return tag
        return None

    def _working_tree_paths(self):
        changes = self._run_git(
            "status", "--porcelain", "--untracked-files=normal"
        )
        return [line[3:].strip().strip('"') for line in changes.splitlines()]

    def _check_updates(self):
        try:
            repository_url, branch = self._repository_and_branch()
            remote_line = subprocess.run(
                ["git", "ls-remote", repository_url, f"refs/heads/{branch}"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            ).stdout.strip()
            if not remote_line:
                raise RuntimeError(
                    f"No remote branch named '{branch}' was found at {repository_url}."
                )
            remote_commit = remote_line.split()[0]

            if self._is_git_repository():
                local_commit = self._run_git("rev-parse", "HEAD")
                if local_commit == remote_commit:
                    status = f"Up to date on {branch} ({remote_commit[:12]})."
                else:
                    status = (
                        f"An update is available on {branch}: "
                        f"{local_commit[:12]} -> {remote_commit[:12]}."
                    )
            else:
                status = (
                    f"Remote {branch} is available at {remote_commit[:12]}. "
                    "Convert this install to Git or download the ZIP."
                )
            self.repository_status.setText(status)
        except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Update check failed", str(error))

    def _convert_to_git(self):
        try:
            if self._is_git_repository():
                QMessageBox.information(
                    self, "Already tracked", "This installation is already a Git repository."
                )
                self._refresh_install_state()
                return
            repository_url, branch = self._repository_and_branch()
            version_tag = self._matching_version_tag(repository_url)
        except (RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Cannot convert install", str(error))
            return

        answer = QMessageBox.question(
            self,
            "Convert installation to Git",
            "This adds Git tracking to the current installation without replacing "
            "its files. The working files must match the selected remote branch "
            "before Git can safely pull updates. ZIP download remains available.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._run_git("init")
            self._run_git("symbolic-ref", "HEAD", f"refs/heads/{branch}")
            self._run_git("remote", "add", "origin", repository_url)
            self._run_git("fetch", "origin", branch, timeout=300)
            if version_tag:
                self._run_git(
                    "fetch",
                    "origin",
                    f"refs/tags/{version_tag}:refs/tags/{version_tag}",
                    timeout=300,
                )
                starting_ref = f"refs/tags/{version_tag}"
            else:
                starting_ref = f"origin/{branch}"
            self._run_git("reset", "--mixed", starting_ref)
            self._run_git(
                "branch", f"--set-upstream-to=origin/{branch}", branch
            )
            changed_paths = self._working_tree_paths()
        except RuntimeError as error:
            QMessageBox.critical(
                self,
                "Git conversion failed",
                "Git could not finish converting this installation. No project "
                f"files were replaced.\n\n{error}\n\n"
                "If Git initialization already started, the folder may contain "
                "a partial .git directory.",
            )
            self._refresh_install_state()
            return

        config_changed = "config/environment_config.json"
        project_changes = [
            path for path in changed_paths if path != config_changed
        ]
        if project_changes:
            self.repository_status.setText(
                "Git tracking is enabled, but local files differ from the remote. "
                "Git pull will be blocked until those differences are resolved."
            )
        elif changed_paths:
            self.repository_status.setText(
                "Git tracking is enabled. Local configuration differences will be "
                "preserved when pulling updates."
            )
        else:
            self.repository_status.setText(
                f"Git tracking is enabled and matches "
                f"{version_tag or branch}."
            )
        self.convert_button.setEnabled(False)
        QMessageBox.information(
            self,
            "Git conversion complete",
            f"This installation is now tracked from {version_tag or branch}. "
            "Existing files were not replaced. "
            "A pull is allowed only when local project files are safe to update.",
        )

    @staticmethod
    def _merge_config(defaults, local_values):
        merged = dict(defaults)
        for key, value in local_values.items():
            if isinstance(merged.get(key), dict) and isinstance(value, dict):
                merged[key] = UpdateManagementWidget._merge_config(
                    merged[key], value
                )
            else:
                merged[key] = value
        return merged

    def _pull_updates(self):
        try:
            repository_url, branch = self._repository_and_branch()
            if not self._is_git_repository():
                raise RuntimeError(
                    "Convert this installation to Git before pulling updates."
                )

            changed_paths = self._working_tree_paths()
            config_relative_path = "config/environment_config.json"
            unexpected = [
                path for path in changed_paths if path != config_relative_path
            ]
            if unexpected:
                raise RuntimeError(
                    "Git pull was stopped because non-configuration files have "
                    "local changes. Preserve or resolve these files first:\n"
                    + "\n".join(unexpected)
                )

            config_path = self.project_root / config_relative_path
            original_config_text = config_path.read_text(encoding="utf-8")
            local_environment = json.loads(original_config_text)
            if config_relative_path in changed_paths:
                self._run_git("reset", "--", config_relative_path)
                self._run_git("checkout", "--", config_relative_path)
            try:
                self._run_git(
                    "fetch", repository_url, branch, timeout=300
                )
                self._run_git("merge", "--ff-only", "FETCH_HEAD", timeout=300)
            except RuntimeError:
                write_json_atomic(config_path, local_environment)
                raise

            updated_environment = json.loads(
                config_path.read_text(encoding="utf-8")
            )
            preserved = dict(local_environment)
            preserved["project"] = updated_environment.get("project", {})
            merged_environment = self._merge_config(updated_environment, preserved)
            write_json_atomic(config_path, merged_environment)
            self.config.environment = merged_environment
            self.repository_status.setText(
                f"Updated from {branch}. Restart the application to load updated code."
            )
            QMessageBox.information(
                self,
                "Update complete",
                "The Git update was applied. Your local configuration values were "
                "preserved. Restart the application to load updated code.",
            )
        except (OSError, json.JSONDecodeError, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Update failed", str(error))

    @staticmethod
    def _github_archive_url(repository_url, branch):
        parsed_url = urllib.parse.urlparse(repository_url)
        if parsed_url.hostname != "github.com":
            raise ValueError(
                "ZIP downloads currently require a repository hosted on github.com."
            )
        parts = [part for part in parsed_url.path.strip("/").split("/") if part]
        if len(parts) != 2:
            raise ValueError("Enter a GitHub repository URL in owner/repository form.")
        owner, repository = parts
        repository = re.sub(r"\.git$", "", repository)
        if not owner or not repository:
            raise ValueError("The GitHub repository URL is incomplete.")
        archive_branch = urllib.parse.quote(branch, safe="/")
        return (
            f"https://api.github.com/repos/{owner}/{repository}/zipball/"
            f"{archive_branch}",
            repository,
        )

    def _download_zip(self):
        try:
            repository_url, branch = self._repository_and_branch()
            archive_url, repository_name = self._github_archive_url(
                repository_url, branch
            )
        except ValueError as error:
            QMessageBox.warning(self, "Cannot download ZIP", str(error))
            return

        suggested_path = str(
            Path.home() / "Downloads" / f"{repository_name}-{branch.replace('/', '-')}.zip"
        )
        target_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save project ZIP",
            suggested_path,
            "ZIP archives (*.zip)",
        )
        if not target_name:
            return

        target_path = Path(target_name)
        if target_path.exists():
            answer = QMessageBox.question(
                self,
                "Replace downloaded ZIP?",
                f"The file already exists:\n{target_path}\n\nReplace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        temporary_path = target_path.with_suffix(target_path.suffix + ".part")
        try:
            request = urllib.request.Request(
                archive_url,
                headers={"User-Agent": "NMS-Dynamic-Suit-Voice"},
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                with temporary_path.open("wb") as file:
                    while chunk := response.read(1024 * 1024):
                        file.write(chunk)
            os.replace(temporary_path, target_path)
        except (OSError, urllib.error.URLError) as error:
            if temporary_path.exists():
                temporary_path.unlink()
            QMessageBox.critical(
                self, "ZIP download failed", f"Could not download the update:\n{error}"
            )
            return

        QMessageBox.information(
            self,
            "ZIP downloaded",
            f"Saved the update ZIP to:\n{target_path}\n\n"
            "Back up your configuration, extract the ZIP over the existing "
            "installation, then run 'py -3.11 installer.py' from the project "
            "folder again.",
        )

    def gather_settings(self):
        updates = self.config.environment.setdefault("updates", {})
        updates["enabled"] = self.updates_enabled.isChecked()
        updates["repository_url"] = self.repository_edit.text().strip()
        updates["branch"] = self.branch_edit.text().strip()
