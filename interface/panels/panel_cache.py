# interface/panels/panel_cache.py
import shutil
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from interface.panels.widgets.buildcard import build_card
from interface.panels.widgets.cache_management import CacheManagementWidget
from pipeline.debug_support import debug_error_message
from pipeline.localization import t
from pipeline.quick_cache import QuickCacheEngine


class CacheTopUpWorker(QThread):
    """Enqueues missing WEM variations off the main UI thread."""
    finished_enqueuing = Signal(int, int)  # (wem_count, jobs_queued)
    failed = Signal(str)

    def __init__(self, config, wem_ids, max_count):
        super().__init__()
        self.config = config
        self.wem_ids = [str(w) for w in wem_ids]
        self.max_count = max_count

    def run(self):
        try:
            qce = getattr(self.config, "quick_cache", None)
            if qce is None:
                qce = QuickCacheEngine(self.config)
                self.config.quick_cache = qce

            jobs_queued = 0
            for wem_id in self.wem_ids:
                wem_dir = self.config.quick_cache_dir / wem_id
                wem_dir.mkdir(parents=True, exist_ok=True)
                existing_count = len(list(wem_dir.glob("*.wem")))
                missing = self.max_count - existing_count
                if missing > 0:
                    for _ in range(missing):
                        qce.enqueue_job(qce._replacement_wrapper, wem_id, wem_dir)
                        jobs_queued += 1
            self.finished_enqueuing.emit(len(self.wem_ids), jobs_queued)
        except Exception as exc:
            self.failed.emit(debug_error_message(exc, t("UI_PANEL_CACHE_001")))


class ChamberRefreshWorker(QThread):
    """Swaps ready quick-cache WEMs into mod_dir and queues generation for uncached chambered IDs."""
    finished_chamber_swap = Signal(int, int, int)  # (total_chambered, swapped_instant, queued_fresh)
    failed = Signal(str)

    def __init__(self, config, max_count: int):
        super().__init__()
        self.config = config
        self.max_count = max_count

    def run(self):
        try:
            qce = getattr(self.config, "quick_cache", None)
            if qce is None:
                qce = QuickCacheEngine(self.config)
                self.config.quick_cache = qce

            mod_wems = sorted(self.config.mod_dir.glob("*.wem"))
            swapped_instant = 0
            queued_fresh = 0

            for mod_wem in mod_wems:
                wem_id = mod_wem.stem
                wem_dir = self.config.quick_cache_dir / wem_id
                cached_files = sorted(wem_dir.glob("*.wem")) if wem_dir.exists() else []

                if cached_files:
                    moved = qce.move_cachedfile_to_mod_dir(cached_files[0], self.config.mod_dir, wem_id)
                    if moved is not None:
                        swapped_instant += 1
                        entry = self.config.intent_map.get(wem_id, {})
                        if str(entry.get("Used", "")).strip().lower() == "yes":
                            remaining = len(list(wem_dir.glob("*.wem")))
                            missing = max(0, self.max_count - remaining)
                            for _ in range(missing):
                                qce.enqueue_job(qce._replacement_wrapper, wem_id, wem_dir)
                else:
                    if wem_id in self.config.intent_map:
                        qce.enqueue_job(qce._chamber_replacement_wrapper, wem_id)
                        queued_fresh += 1

            self.finished_chamber_swap.emit(len(mod_wems), swapped_instant, queued_fresh)
        except Exception as exc:
            self.failed.emit(debug_error_message(exc, t("UI_PANEL_CACHE_002")))


class CachePanel(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._worker: CacheTopUpWorker | None = None
        self._chamber_worker: ChamberRefreshWorker | None = None
        self._build_ui()
        self._populate_wem_selector()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 1. Compact storage & horizon bar
        self.global_cache_widget = CacheManagementWidget(self.config)
        if (inner_layout := self.global_cache_widget.layout()) is not None:
            inner_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.global_cache_widget)

        # 2. Granular WEM Cache & Mod Directory Operations Card
        wem_card, wem_layout = build_card(t("UI_PANEL_CACHE_003"))

        self.core_warning_label = QLabel(t("UI_PANEL_CACHE_004"))
        self.core_warning_label.setWordWrap(True)
        self.core_warning_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.core_warning_label.setStyleSheet(
            "background-color: #141923; border: 1px solid #ffaa00; "
            "border-radius: 6px; padding: 8px 10px; color: #ffdd88;"
        )
        wem_layout.addWidget(self.core_warning_label)

        wem_layout.addWidget(QLabel(t("UI_PANEL_CACHE_005")))
        self.wem_selector = QComboBox()
        self.wem_selector.setEditable(True)
        self.wem_selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if (completer := self.wem_selector.completer()) is not None:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.wem_selector.currentIndexChanged.connect(self._on_wem_selected)
        wem_layout.addWidget(self.wem_selector)

        meta_row = QHBoxLayout()
        self.wem_status_label = QLabel(t("UI_PANEL_CACHE_006", existing=0, max_count=16))
        self.used_checkbox = QCheckBox(t("UI_PANEL_CACHE_007"))
        self.used_checkbox.toggled.connect(self._on_used_toggled)
        meta_row.addWidget(self.wem_status_label)
        meta_row.addStretch()
        meta_row.addWidget(self.used_checkbox)
        wem_layout.addLayout(meta_row)

        # Row 1: Selected WEM Purge / Top Up
        selected_btn_row = QHBoxLayout()
        self.clear_selected_btn = QPushButton(t("UI_PANEL_CACHE_008"))
        self.clear_selected_btn.clicked.connect(self._clear_selected_wem)

        self.topup_selected_btn = QPushButton(t("UI_PANEL_CACHE_009"))
        self.topup_selected_btn.clicked.connect(self._topup_selected_wem)

        selected_btn_row.addWidget(self.clear_selected_btn)
        selected_btn_row.addWidget(self.topup_selected_btn)
        wem_layout.addLayout(selected_btn_row)

        # Row 2: All Confirmed 'Used' Purge / Top Up
        used_btn_row = QHBoxLayout()
        self.purge_used_btn = QPushButton(t("UI_PANEL_CACHE_010"))
        self.purge_used_btn.clicked.connect(self._purge_all_used_wems)

        self.topup_all_btn = QPushButton(t("UI_PANEL_CACHE_011"))
        self.topup_all_btn.clicked.connect(self._topup_all_used_wems)

        used_btn_row.addWidget(self.purge_used_btn)
        used_btn_row.addWidget(self.topup_all_btn)
        wem_layout.addLayout(used_btn_row)

        # Row 3: Global Cache Purge / Replace All Chambered Mod WEMs
        global_btn_row = QHBoxLayout()
        self.purge_all_btn = QPushButton(t("UI_PANEL_CACHE_012"))
        self.purge_all_btn.clicked.connect(self._purge_all_quick_cache)

        self.refresh_chambered_btn = QPushButton(t("UI_PANEL_CACHE_013"))
        self.refresh_chambered_btn.setToolTip(t("UI_PANEL_CACHE_014"))
        self.refresh_chambered_btn.clicked.connect(self._replace_all_chambered_wems)

        global_btn_row.addWidget(self.purge_all_btn)
        global_btn_row.addWidget(self.refresh_chambered_btn)
        wem_layout.addLayout(global_btn_row)

        btn_style = """
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
            QPushButton:disabled {
                background-color: #1c2430;
                color: #7a869a;
                border: 1px solid #2e3846;
            }
        """
        for btn in (
            self.clear_selected_btn,
            self.topup_selected_btn,
            self.purge_used_btn,
            self.topup_all_btn,
            self.purge_all_btn,
            self.refresh_chambered_btn,
        ):
            btn.setStyleSheet(btn_style)

        self.queue_feedback_label = QLabel("")
        self.queue_feedback_label.setWordWrap(True)
        wem_layout.addWidget(self.queue_feedback_label)

        layout.addWidget(wem_card)
        layout.addStretch()

    def _populate_wem_selector(self):
        self.wem_selector.blockSignals(True)
        self.wem_selector.clear()

        intent_map = getattr(self.config, "intent_map", {})
        for wem_id, data in sorted(intent_map.items(), key=lambda item: str(item[0])):
            phrase = data.get("Transcription", "").strip()
            used_tag = "" if str(data.get("Used", "")).strip().lower() == "yes" else f" {t('UI_PANEL_CACHE_015')}"
            display_text = f"{wem_id} — {phrase}{used_tag}"
            self.wem_selector.addItem(display_text, userData=str(wem_id))

        self.wem_selector.blockSignals(False)
        if self.wem_selector.count() > 0:
            self._on_wem_selected(0)

    def _current_wem_id(self):
        idx = self.wem_selector.currentIndex()
        if idx < 0:
            return None
        return self.wem_selector.itemData(idx)

    def _on_wem_selected(self, _index):
        wem_id = self._current_wem_id()
        if not wem_id:
            return

        entry = self.config.intent_map.get(wem_id, {})
        is_used = str(entry.get("Used", "")).strip().lower() == "yes"

        self.used_checkbox.blockSignals(True)
        self.used_checkbox.setChecked(is_used)
        self.used_checkbox.blockSignals(False)

        self._refresh_selected_wem_stats()

    def _refresh_selected_wem_stats(self):
        wem_id = self._current_wem_id()
        if not wem_id:
            return
        max_count = self.global_cache_widget.cache_horizon_spin.value()
        wem_dir = self.config.quick_cache_dir / str(wem_id)
        existing = len(list(wem_dir.glob("*.wem"))) if wem_dir.exists() else 0
        self.wem_status_label.setText(
            t("UI_PANEL_CACHE_016", wem_id=wem_id, existing=existing, max_count=max_count)
        )

    def _on_used_toggled(self, checked):
        wem_id = self._current_wem_id()
        if not wem_id or wem_id not in self.config.intent_map:
            return

        new_val = "Yes" if checked else "No"
        self.config.intent_map[wem_id]["Used"] = new_val

        idx = self.wem_selector.currentIndex()
        phrase = self.config.intent_map[wem_id].get("Transcription", "").strip()
        used_tag = "" if checked else f" {t('UI_PANEL_CACHE_015')}"
        self.wem_selector.setItemText(idx, f"{wem_id} — {phrase}{used_tag}")

        if hasattr(self.config, "save_intent_map"):
            self.config.save_intent_map()

    def _is_core_engaged(self) -> bool:
        if getattr(self.config, "llm", None) is None:
            QMessageBox.warning(
                self,
                t("UI_PANEL_CACHE_017"),
                t("UI_PANEL_CACHE_018"),
            )
            return False
        return True

    def _clear_selected_wem(self):
        wem_id = self._current_wem_id()
        if not wem_id:
            return

        wem_dir = self.config.quick_cache_dir / str(wem_id)
        if not wem_dir.exists() or not any(wem_dir.iterdir()):
            QMessageBox.information(
                self,
                t("UI_PANEL_CACHE_019"),
                t("UI_PANEL_CACHE_020", wem_id=wem_id),
            )
            return

        answer = QMessageBox.question(
            self,
            t("UI_PANEL_CACHE_021"),
            t("UI_PANEL_CACHE_022", wem_id=wem_id),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            shutil.rmtree(wem_dir)
            self.queue_feedback_label.setStyleSheet("color: #88dd88; font-weight: bold;")
            self.queue_feedback_label.setText(t("UI_PANEL_CACHE_023", wem_id=wem_id))
            self._refresh_selected_wem_stats()
            self.global_cache_widget.refresh_stats()
        except OSError as error:
            QMessageBox.critical(
                self,
                t("UI_PANEL_CACHE_024"),
                debug_error_message(error, t("UI_PANEL_CACHE_025", wem_id=wem_id)),
            )

    def _purge_all_used_wems(self):
        used_ids = [
            str(wem_id)
            for wem_id, data in self.config.intent_map.items()
            if str(data.get("Used", "")).strip().lower() == "yes"
        ]
        if not used_ids:
            QMessageBox.information(self, t("UI_PANEL_CACHE_026"), t("UI_PANEL_CACHE_027"))
            return

        answer = QMessageBox.question(
            self,
            t("UI_PANEL_CACHE_028"),
            t("UI_PANEL_CACHE_029", count=len(used_ids)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            removed = 0
            for wem_id in used_ids:
                wem_dir = self.config.quick_cache_dir / wem_id
                if wem_dir.exists():
                    shutil.rmtree(wem_dir)
                    removed += 1
            self.queue_feedback_label.setStyleSheet("color: #88dd88; font-weight: bold;")
            self.queue_feedback_label.setText(t("UI_PANEL_CACHE_030", removed=removed))
            self._refresh_selected_wem_stats()
            self.global_cache_widget.refresh_stats()
        except OSError as error:
            QMessageBox.critical(
                self,
                t("UI_PANEL_CACHE_031"),
                debug_error_message(error, t("UI_PANEL_CACHE_032")),
            )

    def _purge_all_quick_cache(self):
        if self.global_cache_widget.purge_all_caches():
            self.queue_feedback_label.setStyleSheet("color: #88dd88; font-weight: bold;")
            self.queue_feedback_label.setText(t("UI_PANEL_CACHE_033"))
            self._refresh_selected_wem_stats()

    def _topup_selected_wem(self):
        if not self._is_core_engaged():
            return
        wem_id = self._current_wem_id()
        if not wem_id:
            return
        max_count = self.global_cache_widget.cache_horizon_spin.value()
        self._start_topup_worker([wem_id], max_count)

    def _topup_all_used_wems(self):
        if not self._is_core_engaged():
            return
        used_ids = [
            str(wem_id)
            for wem_id, data in self.config.intent_map.items()
            if str(data.get("Used", "")).strip().lower() == "yes"
        ]
        if not used_ids:
            QMessageBox.information(self, t("UI_PANEL_CACHE_026"), t("UI_PANEL_CACHE_027"))
            return

        max_count = self.global_cache_widget.cache_horizon_spin.value()
        answer = QMessageBox.question(
            self,
            t("UI_PANEL_CACHE_034"),
            t("UI_PANEL_CACHE_035", max_count=max_count, count=len(used_ids)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._start_topup_worker(used_ids, max_count)

    def _start_topup_worker(self, wem_ids, max_count):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.warning(self, t("UI_PANEL_CACHE_036"), t("UI_PANEL_CACHE_037"))
            return

        is_bulk = len(wem_ids) > 1
        self._set_buttons_enabled(False, active_bulk=is_bulk)
        self.queue_feedback_label.setStyleSheet("color: #66b2ff; font-weight: bold;")
        self.queue_feedback_label.setText(t("UI_PANEL_CACHE_038"))
        QApplication.processEvents()

        worker = CacheTopUpWorker(self.config, wem_ids, max_count)
        worker.finished_enqueuing.connect(self._on_topup_finished)
        worker.failed.connect(self._on_topup_failed)
        self._worker = worker
        worker.start()

    def _set_buttons_enabled(self, enabled, active_bulk: bool = False):
        for btn in (
            self.clear_selected_btn,
            self.topup_selected_btn,
            self.purge_used_btn,
            self.topup_all_btn,
            self.purge_all_btn,
            self.refresh_chambered_btn,
        ):
            btn.setEnabled(enabled)

        if enabled:
            self.topup_selected_btn.setText(t("UI_PANEL_CACHE_009"))
            self.topup_all_btn.setText(t("UI_PANEL_CACHE_011"))
        else:
            if active_bulk:
                self.topup_all_btn.setText(t("UI_PANEL_CACHE_039"))
            else:
                self.topup_selected_btn.setText(t("UI_PANEL_CACHE_040"))

    def _on_topup_finished(self, wem_count, jobs_queued):
        self._set_buttons_enabled(True)
        self._refresh_selected_wem_stats()
        self.global_cache_widget.refresh_stats()
        self.queue_feedback_label.setStyleSheet("color: #88dd88; font-weight: bold;")
        self.queue_feedback_label.setText(
            t("UI_PANEL_CACHE_041", wem_count=wem_count, jobs_queued=jobs_queued)
        )

    def _on_topup_failed(self, error_msg):
        self._set_buttons_enabled(True)
        self.queue_feedback_label.setText(t("UI_PANEL_CACHE_042"))
        QMessageBox.critical(self, t("UI_PANEL_CACHE_043"), error_msg)

    def _replace_all_chambered_wems(self):
        if not self._is_core_engaged():
            return
        if self._chamber_worker is not None and self._chamber_worker.isRunning():
            QMessageBox.warning(self, t("UI_PANEL_CACHE_036"), t("UI_PANEL_CACHE_044"))
            return

        mod_wems = list(self.config.mod_dir.glob("*.wem"))
        if not mod_wems:
            QMessageBox.information(
                self,
                t("UI_PANEL_CACHE_045"),
                t("UI_PANEL_CACHE_046", mod_dir=self.config.mod_dir),
            )
            return

        answer = QMessageBox.question(
            self,
            t("UI_PANEL_CACHE_047"),
            t("UI_PANEL_CACHE_048", count=len(mod_wems)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._set_buttons_enabled(False)
        self.queue_feedback_label.setStyleSheet("color: #66b2ff; font-weight: bold;")
        self.queue_feedback_label.setText(t("UI_PANEL_CACHE_049"))
        QApplication.processEvents()

        max_count = self.global_cache_widget.cache_horizon_spin.value()
        worker = ChamberRefreshWorker(self.config, max_count)
        worker.finished_chamber_swap.connect(self._on_chamber_swap_finished)
        worker.failed.connect(self._on_topup_failed)
        self._chamber_worker = worker
        worker.start()

    def _on_chamber_swap_finished(self, total_chambered, swapped_instant, queued_fresh):
        self._set_buttons_enabled(True)
        self._refresh_selected_wem_stats()
        self.global_cache_widget.refresh_stats()
        self.queue_feedback_label.setStyleSheet("color: #88dd88; font-weight: bold;")
        self.queue_feedback_label.setText(
            t(
                "UI_PANEL_CACHE_050",
                total_chambered=total_chambered,
                swapped_instant=swapped_instant,
                queued_fresh=queued_fresh,
            )
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.global_cache_widget.refresh_stats()
        self._refresh_selected_wem_stats()

    def gather_settings(self):
        self.global_cache_widget.gather_settings()
