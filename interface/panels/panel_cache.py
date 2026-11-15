# interface/panels/panel_cache.py
import shutil
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication
)

from interface.panels.widgets.buildcard import build_card
from interface.panels.widgets.cache_management import CacheManagementWidget
from pipeline.debug_support import debug_error_message
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
            self.failed.emit(debug_error_message(exc, "Queuing cache top-up"))


class CachePanel(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._worker: CacheTopUpWorker | None = None
        self._build_ui()
        self._populate_wem_selector()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 1. Reuse existing modular storage & global purge widget
        self.global_cache_widget = CacheManagementWidget(self.config)
        if (inner_layout := self.global_cache_widget.layout()) is not None:
            inner_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.global_cache_widget)

        # 2. Granular WEM Cache & Top-Up Card
        wem_card, wem_layout = build_card("VOICE LINE QUICK-CACHE OPERATIONS")

        self.core_warning_label = QLabel(
            "WARNING: Engage AI Core before undertaking cache replenishment operations. "
            "No Man's Sky does not need to be running."
        )
        self.core_warning_label.setWordWrap(True)
        self.core_warning_label.setStyleSheet(
            "background-color: #141923; border: 1px solid #ffaa00; "
            "border-radius: 6px; padding: 10px; color: #ffdd88;"
        )
        wem_layout.addWidget(self.core_warning_label)
        wem_layout.addSpacing(6)

        wem_layout.addWidget(QLabel("Select Voice Line (WEM ID — Original Transcription):"))
        self.wem_selector = QComboBox()
        self.wem_selector.setEditable(True)
        self.wem_selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if (completer := self.wem_selector.completer()) is not None:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.wem_selector.currentIndexChanged.connect(self._on_wem_selected)
        wem_layout.addWidget(self.wem_selector)

        # Metadata & Used Flag Row
        meta_row = QHBoxLayout()
        self.wem_status_label = QLabel("Cached variations: 0 / 16")
        self.used_checkbox = QCheckBox("Confirmed as Used by current game build")
        self.used_checkbox.toggled.connect(self._on_used_toggled)
        meta_row.addWidget(self.wem_status_label)
        meta_row.addStretch()
        meta_row.addWidget(self.used_checkbox)
        wem_layout.addLayout(meta_row)

        # Selected WEM Action Buttons
        selected_btn_row = QHBoxLayout()
        self.topup_selected_btn = QPushButton("TOP UP SELECTED WEM TO MAX")
        self.topup_selected_btn.clicked.connect(self._topup_selected_wem)

        self.clear_selected_btn = QPushButton("CLEAR SELECTED WEM CACHE")
        self.clear_selected_btn.clicked.connect(self._clear_selected_wem)

        selected_btn_row.addWidget(self.topup_selected_btn)
        selected_btn_row.addWidget(self.clear_selected_btn)
        wem_layout.addLayout(selected_btn_row)

        wem_layout.addSpacing(10)

        # Bulk Top-Up Action
        self.topup_all_btn = QPushButton("TOP UP ALL 'USED' WEMS TO CURRENT MAX")
        self.topup_all_btn.clicked.connect(self._topup_all_used_wems)
        wem_layout.addWidget(self.topup_all_btn)

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
        for btn in (self.topup_selected_btn, self.clear_selected_btn, self.topup_all_btn):
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
            used_tag = "" if str(data.get("Used", "")).strip().lower() == "yes" else " [UNUSED]"
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
        self.wem_status_label.setText(f"Cached variations for {wem_id}: {existing} / {max_count}")

    def _on_used_toggled(self, checked):
        wem_id = self._current_wem_id()
        if not wem_id or wem_id not in self.config.intent_map:
            return

        new_val = "Yes" if checked else "No"
        self.config.intent_map[wem_id]["Used"] = new_val

        idx = self.wem_selector.currentIndex()
        phrase = self.config.intent_map[wem_id].get("Transcription", "").strip()
        used_tag = "" if checked else " [UNUSED]"
        self.wem_selector.setItemText(idx, f"{wem_id} — {phrase}{used_tag}")

        if hasattr(self.config, "save_intent_map"):
            self.config.save_intent_map()

    def _is_core_engaged(self) -> bool:
        if getattr(self.config, "llm", None) is None:
            QMessageBox.warning(
                self,
                "AI Core Not Engaged",
                "Please click ENGAGE AI CORE before starting cache replenishment operations.\n\n"
                "(No Man's Sky does not need to be open.)",
            )
            return False
        return True

    def _clear_selected_wem(self):
        wem_id = self._current_wem_id()
        if not wem_id:
            return

        wem_dir = self.config.quick_cache_dir / str(wem_id)
        if not wem_dir.exists() or not any(wem_dir.iterdir()):
            QMessageBox.information(self, "Nothing to clear", f"No cached files exist for WEM {wem_id}.")
            return

        answer = QMessageBox.question(
            self,
            "Confirm WEM cache clear",
            f"Delete all cached variations for WEM {wem_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            shutil.rmtree(wem_dir)
            self.queue_feedback_label.setStyleSheet("color: #88dd88; font-weight: bold;")
            self.queue_feedback_label.setText(f"Cleared cached variations for WEM {wem_id}.")
            self._refresh_selected_wem_stats()
            self.global_cache_widget.refresh_stats()
        except OSError as error:
            QMessageBox.critical(
                self, "Clear failed", debug_error_message(error, f"Clearing WEM {wem_id}")
            )

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
            QMessageBox.information(self, "No used WEMs", "No WEMs are currently marked as Used.")
            return

        max_count = self.global_cache_widget.cache_horizon_spin.value()
        answer = QMessageBox.question(
            self,
            "Confirm Bulk Top-Up",
            f"Queue cache generation up to {max_count} variations for {len(used_ids)} used WEMs?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._start_topup_worker(used_ids, max_count)

    def _start_topup_worker(self, wem_ids, max_count):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "A cache top-up job is already being queued.")
            return

        is_bulk = len(wem_ids) > 1
        self._set_buttons_enabled(False, active_bulk=is_bulk)
        self.queue_feedback_label.setStyleSheet("color: #66b2ff; font-weight: bold;")
        self.queue_feedback_label.setText("Button triggered — scanning cache directories...")
        QApplication.processEvents()

        worker = CacheTopUpWorker(self.config, wem_ids, max_count)
        worker.finished_enqueuing.connect(self._on_topup_finished)
        worker.failed.connect(self._on_topup_failed)
        self._worker = worker
        worker.start()

    def _set_buttons_enabled(self, enabled, active_bulk: bool = False):
        self.topup_selected_btn.setEnabled(enabled)
        self.clear_selected_btn.setEnabled(enabled)
        self.topup_all_btn.setEnabled(enabled)

        if enabled:
            self.topup_selected_btn.setText("TOP UP SELECTED WEM TO MAX")
            self.topup_all_btn.setText("TOP UP ALL 'USED' WEMS TO CURRENT MAX")
        else:
            if active_bulk:
                self.topup_all_btn.setText("WORKING — TOPPING UP ALL 'USED' WEMS...")
            else:
                self.topup_selected_btn.setText("WORKING — TOPPING UP SELECTED WEM...")

    def _on_topup_finished(self, wem_count, jobs_queued):
        self._set_buttons_enabled(True)
        self._refresh_selected_wem_stats()
        self.global_cache_widget.refresh_stats()
        self.queue_feedback_label.setText(
            f"Scan complete across {wem_count} WEM(s): queued {jobs_queued} new generation job(s)."
            )

    def _on_topup_failed(self, error_msg):
        self._set_buttons_enabled(True)
        self.queue_feedback_label.setText("Failed to queue top-up jobs.")
        QMessageBox.critical(self, "Top-Up Error", error_msg)

    def showEvent(self, event):
        super().showEvent(event)
        self.global_cache_widget.refresh_stats()
        self._refresh_selected_wem_stats()

    def gather_settings(self):
        self.global_cache_widget.gather_settings()