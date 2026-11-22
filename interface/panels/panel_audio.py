import json
import importlib
import threading
import wave
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox,
    QPushButton, QLineEdit, QTextEdit, QCheckBox
)
from pipeline.debug_support import debug_error_message


class AudioPanel(QWidget):
    log_signal = Signal(str)
    reset_btn_signal = Signal(bool)

    def __init__(self, config):
        super().__init__()
        self.config = config

        self.presets_file = Path(__file__).parent.parent.parent / "data" / "audio_presets.json"
        self.loaded_presets = {}
        self.preset_options = ["Browse Custom Voice Signatures..."]

        if self.presets_file.exists():
            try:
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    self.loaded_presets = json.load(f)
                self.preset_options.extend(list(self.loaded_presets.keys()))
            except Exception as e:
                message = debug_error_message(e, "Loading saved audio presets")
                print(f"[PRESET ERROR]: Failed to parse audio_presets.json: {message}")

        self.log_signal.connect(self._append_console_log)
        self.reset_btn_signal.connect(self._set_button_lock_state)

        self.voice_catalog = self.config.ttm_voices_data
        self.available_voices = self._get_voices_for_bin(self.config.tts_voice_bin_name)
        if not self.available_voices:
            self.available_voices = list(self.voice_catalog.keys())

        self._build_ui()
        self._initialize_data_fields()

    def _build_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setSpacing(15)
        master_layout.setContentsMargins(15, 15, 15, 15)

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        preset_group = QWidget()
        preset_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setContentsMargins(15, 12, 15, 12)
        preset_layout.setSpacing(10)

        preset_header = QLabel("QUICK EXOSUIT CHARACTER PROFILES")
        preset_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        preset_layout.addWidget(preset_header)

        preset_row = QHBoxLayout()
        preset_label = QLabel("Precalibrated Vocal Signatures:")
        preset_label.setStyleSheet("border: none; color: #ffffff;")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.preset_options)
        self.preset_combo.setMinimumWidth(260)
        self.preset_combo.setStyleSheet("background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; padding: 4px; color: #ffffff;")
        self.preset_combo.currentTextChanged.connect(self._on_character_preset_selected)
        preset_row.addWidget(preset_label)
        preset_row.addWidget(self.preset_combo)
        preset_row.addStretch()
        preset_layout.addLayout(preset_row)

        voice_row = QHBoxLayout()
        voice_label = QLabel("Available Exosuit Base Voices:")
        voice_label.setStyleSheet("border: none; color: #ffffff;")
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(self.available_voices)
        self.voice_combo.setMinimumWidth(260)
        self.voice_combo.setStyleSheet("background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; padding: 4px; color: #ffffff;")
        self.voice_combo.currentTextChanged.connect(self._on_base_voice_selected)
        voice_row.addWidget(voice_label)
        voice_row.addWidget(self.voice_combo)
        voice_row.addStretch()
        preset_layout.addLayout(voice_row)

        self.voice_desc_box = QLabel("Identity Signature: Loading profile arrays...")
        self.voice_desc_box.setWordWrap(True)
        self.voice_desc_box.setStyleSheet("""
            QLabel { background-color: #0c0c0e; border: 1px dashed #1f2430; color: #5c6773;
                     padding: 6px; font-family: 'Consolas', monospace; font-size: 11px; border-radius: 4px; }
        """)
        preset_layout.addWidget(self.voice_desc_box)
        left_layout.addWidget(preset_group)

        primary_group = QWidget()
        primary_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        primary_layout = QVBoxLayout(primary_group)
        primary_layout.setContentsMargins(15, 12, 15, 12)
        primary_layout.setSpacing(12)

        primary_header = QLabel("PRIMARY EXOSUIT AUDIO TUNING")
        primary_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        primary_layout.addWidget(primary_header)

        self.lufs_slider, self.lufs_val_label, self.loudness_toggle = self._create_slider_row(
            primary_layout,
            "Target Loudness (LUFS) [Baseline: -11.0]:",
            -220, -80, -110,
            self._on_slider_changed
        )
        self.peak_slider, self.peak_val_label, _ = self._create_slider_row(
            primary_layout,
            "Peak Headroom Ceiling (dB) [Baseline: 6.0]:",
            20, 80, 60,
            self._on_slider_changed,
            has_toggle=False
        )
        if self.loudness_toggle is not None:
            self.loudness_toggle.toggled.connect(self.peak_slider.setEnabled)

        loudness_note = QLabel(
            "NOTE: Baseline (-11.0 LUFS / 6.0 dB) is calibrated for 100% in-game Voice volume. "
            "Test in-game with defaults first—and adjust the game's Voice slider—before raising these."
        )
        loudness_note.setWordWrap(True)
        loudness_note.setStyleSheet(
            "color: #8a99ad; font-size: 10px; font-family: 'Consolas', monospace; "
            "background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; padding: 5px;"
        )
        primary_layout.addWidget(loudness_note)

        self.tempo_slider, self.tempo_val_label, self.tempo_toggle = self._create_slider_row(
            primary_layout,
            "Sentence Pacing (Speed Only) [Baseline: 1.00x]:",
            50, 200, 100,
            self._on_slider_changed
        )
        self.pitch_slider, self.pitch_val_label, self.pitch_toggle = self._create_slider_row(
            primary_layout,
            "Core Voice Tone (Pitch Only) [Baseline: 0 st]:",
            -12, 12, 0,
            self._on_slider_changed
        )
        self.mix_slider, self.mix_val_label, self.mix_toggle = self._create_slider_row(
            primary_layout,
            "Synthetic Cybernetic Overlay % [Baseline: 10%]:",
            0, 100, 10,
            self._on_slider_changed
        )

        left_layout.addWidget(primary_group)

        advanced_group = QWidget()
        advanced_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setContentsMargins(15, 12, 15, 12)
        advanced_layout.setSpacing(10)

        advanced_header = QLabel("ADVANCED SIGNAL DIAGNOSTICS (FINE TUNING)")
        advanced_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        advanced_layout.addWidget(advanced_header)

        self.rate_slider, self.rate_val_label, self.rate_toggle = self._create_slider_row(
            advanced_layout,
            "Combined Speed + Pitch Warp [Baseline: 1.00]:",
            50, 160, 100,
            self._on_slider_changed
        )
        self.formant_slider, self.formant_val_label, self.formant_toggle = self._create_slider_row(
            advanced_layout,
            "Vocal Resonator / Throat Size % [Baseline: 100%]:",
            40, 160, 100,
            self._on_slider_changed
        )

        throat_hint = QLabel("Throat Size Guide: Lower % (<100%) = Deeper, larger vocal tract | Higher % (>100%) = Tighter, smaller vocal tract")
        throat_hint.setWordWrap(True)
        throat_hint.setStyleSheet("color: #5c6773; font-size: 10px; font-family: 'Consolas', monospace; border: none;")
        advanced_layout.addWidget(throat_hint)

        btn_action_row = QHBoxLayout()
        btn_action_row.setSpacing(10)

        self.reset_profile_btn = QPushButton("RESET TO PROFILE")
        self.reset_profile_btn.setStyleSheet("""
            QPushButton { background-color: #1f2430; border: 1px solid #ffaa00; color: #ffaa00; padding: 6px 12px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #ffaa00; color: #141923; }
        """)
        self.reset_profile_btn.clicked.connect(self._reset_to_saved_userconfig)

        self.restore_baselines_btn = QPushButton("RESTORE SYSTEM BASELINES")
        self.restore_baselines_btn.setStyleSheet("""
            QPushButton { background-color: #1f2430; border: 1px solid #5c6773; color: #ffffff; padding: 6px 12px; font-weight: bold; font-family: 'Consolas', monospace; font-size: 11px; }
            QPushButton:hover { background-color: #5c6773; color: #ffffff; }
        """)
        self.restore_baselines_btn.clicked.connect(self._restore_factory_baselines)

        btn_action_row.addWidget(self.reset_profile_btn)
        btn_action_row.addWidget(self.restore_baselines_btn)
        btn_action_row.addStretch()
        advanced_layout.addLayout(btn_action_row)

        left_layout.addWidget(advanced_group, stretch=1)
        master_layout.addWidget(left_pane, stretch=1)

        right_pane = QWidget()
        right_pane.setMinimumWidth(380)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        sandbox_group = QWidget()
        sandbox_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        sandbox_layout = QVBoxLayout(sandbox_group)
        sandbox_layout.setContentsMargins(15, 15, 15, 15)
        sandbox_layout.setSpacing(10)

        sandbox_header = QLabel("REAL-TIME SYNTHESIS SANDBOX")
        sandbox_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        sandbox_layout.addWidget(sandbox_header)

        input_title = QLabel("Input Live Diagnostic Test Phrase:")
        input_title.setStyleSheet("color: #ffffff; font-size: 11px; border: none;")
        sandbox_layout.addWidget(input_title)

        self.test_text_entry = QLineEdit()
        self.test_text_entry.setText("Units received. Exosuit environmental tuning sequence verified.")
        self.test_text_entry.setStyleSheet("""
            QLineEdit { background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; padding: 6px; color: #ffffff; font-family: 'Segoe UI', sans-serif; }
            QLineEdit:focus { border: 1px solid #ffaa00; }
        """)
        sandbox_layout.addWidget(self.test_text_entry)

        playback_action_row = QHBoxLayout()
        playback_action_row.setSpacing(8)

        self.preview_btn = QPushButton("APPLY EFFECTS & PLAY")
        self.preview_btn.setStyleSheet("""
            QPushButton { background-color: #005588; border: 1px solid #00aaff; color: white; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; }
            QPushButton:hover { background-color: #007acc; border-color: #33bbff; }
            QPushButton:disabled { background-color: #222225; border-color: #444448; color: #66666d; }
        """)
        self.preview_btn.clicked.connect(lambda: self._trigger_async_preview_loop(raw_mode=False))

        self.preview_raw_btn = QPushButton("PLAY RAW")
        self.preview_raw_btn.setStyleSheet("""
            QPushButton { background-color: #1f2430; border: 1px solid #ffaa00; color: #ffaa00; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; }
            QPushButton:hover { background-color: #ffaa00; color: #141923; }
            QPushButton:disabled { background-color: #222225; border-color: #444448; color: #66666d; }
        """)
        self.preview_raw_btn.clicked.connect(lambda: self._trigger_async_preview_loop(raw_mode=True))

        self.stop_playback_btn = QPushButton("STOP")
        self.stop_playback_btn.setStyleSheet("""
            QPushButton { background-color: #880000; border: 1px solid #ff3333; color: white; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; }
            QPushButton:hover { background-color: #aa0000; border-color: #ff5555; }
        """)
        self.stop_playback_btn.clicked.connect(self._abort_active_wave_playback)

        playback_action_row.addWidget(self.preview_btn, stretch=2)
        playback_action_row.addWidget(self.preview_raw_btn, stretch=1)
        playback_action_row.addWidget(self.stop_playback_btn, stretch=1)
        sandbox_layout.addLayout(playback_action_row)

        pipeline_title = QLabel("Tuning Engine Pipeline Output:")
        pipeline_title.setStyleSheet("color: #5c6773; font-size: 11px; border: none; margin-top: 5px;")
        sandbox_layout.addWidget(pipeline_title)

        self.status_log_view = QTextEdit()
        self.status_log_view.setReadOnly(True)
        self.status_log_view.setStyleSheet("""
            QTextEdit { background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; color: #00ff66; font-family: 'Consolas', monospace; font-size: 11px; }
        """)
        self.status_log_view.append(">> Tuning Engine Status: Standby\n>> Ready to process testing audio streams.")
        sandbox_layout.addWidget(self.status_log_view)

        right_layout.addWidget(sandbox_group)
        master_layout.addWidget(right_pane)
    def _create_slider_row(self, parent_layout, label_text, min_val, max_val, default_val, change_callback, has_toggle=True):
        row_frame = QWidget()
        row_frame.setStyleSheet("border: none; background: transparent;")
        row_frame_layout = QHBoxLayout(row_frame)
        row_frame_layout.setContentsMargins(0, 0, 0, 0)

        toggle_box = None
        if has_toggle:
            toggle_box = QCheckBox()
            toggle_box.setChecked(True)
            toggle_box.setToolTip("Enable or bypass this audio modifier")
            toggle_box.setStyleSheet("""
                QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #ffaa00; border-radius: 3px; background: #0c0c0e; }
                QCheckBox::indicator:checked { background: #ffaa00; }
            """)
            row_frame_layout.addWidget(toggle_box)

        title_label = QLabel(label_text)
        title_label.setMinimumWidth(265)
        title_label.setStyleSheet("color: #ffffff; font-size: 11px;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #1f2430; height: 6px; background: #0c0c0e; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffaa00; border: 1px solid #ffaa00; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }
            QSlider::handle:horizontal:hover { background: #ffffff; border-color: #ffaa00; }
            QSlider::handle:horizontal:disabled { background: #4b5668; border-color: #4b5668; }
        """)
        slider.valueChanged.connect(change_callback)

        val_label = QLabel(str(default_val))
        val_label.setFixedWidth(72)
        val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_label.setStyleSheet("font-family: 'Consolas', monospace; color: #ffaa00; font-weight: bold; font-size: 11px;")

        if toggle_box is not None:
            toggle_box.toggled.connect(slider.setEnabled)
            toggle_box.toggled.connect(lambda _: change_callback(slider.value()))

        row_frame_layout.addWidget(title_label)
        row_frame_layout.addWidget(slider, stretch=1)
        row_frame_layout.addWidget(val_label)

        parent_layout.addWidget(row_frame)
        return slider, val_label, toggle_box

    def _initialize_data_fields(self):
        if not self.config or "voice_effects" not in self.config.user_customization:
            return
        effects = self.config.user_customization.get("voice_effects", {})
        self._apply_raw_dictionary_to_sliders(effects)

    def _apply_raw_dictionary_to_sliders(self, data_dict):
        active_voice = data_dict.get("base_voice")
        if active_voice in self.available_voices:
            self.voice_combo.setCurrentText(active_voice)
            self._update_metadata_description_label(active_voice)

        if "loudness_target" in data_dict:
            lufs_val = float(data_dict.get("loudness_target", -11.0))
        else:
            lufs_val = -11.0 + float(data_dict.get("gain_db", 0.0))
        lufs_val = max(-22.0, min(-8.0, lufs_val))

        peak_val = max(2.0, min(8.0, float(data_dict.get("loudness_true_peak", 6.0))))

        self.lufs_slider.setValue(int(round(lufs_val * 10)))
        self.peak_slider.setValue(int(round(peak_val * 10)))
        self.tempo_slider.setValue(int(round(float(data_dict.get("tempo", 1.00)) * 100)))
        self.pitch_slider.setValue(int(data_dict.get("pitch_semitones", 0)))
        self.mix_slider.setValue(int(data_dict.get("ring_mix", 10)))
        self.rate_slider.setValue(int(round(float(data_dict.get("rate", 1.00)) * 100)))
        self.formant_slider.setValue(int(data_dict.get("formant_percent", 100)))

        self._active_ring_freq = int(data_dict.get("ring_freq", 300))

        toggle_map = [
            (self.loudness_toggle, "enable_loudness"),
            (self.tempo_toggle, "enable_tempo"),
            (self.pitch_toggle, "enable_pitch"),
            (self.mix_toggle, "enable_ring"),
            (self.rate_toggle, "enable_rate"),
            (self.formant_toggle, "enable_formant"),
        ]
        for toggle, key in toggle_map:
            if toggle is not None:
                toggle.setChecked(bool(data_dict.get(key, True)))

        self._update_all_text_labels()

    def _on_slider_changed(self, value):
        self._update_all_text_labels()
        if self.preset_combo.currentIndex() != 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)

    def _on_base_voice_selected(self, chosen_voice):
        self._update_metadata_description_label(chosen_voice)
        if self.config and "voice_effects" in self.config.user_customization:
            self.config.user_customization["voice_effects"]["base_voice"] = chosen_voice

    def _update_metadata_description_label(self, voice_key):
        voice_info = self.voice_catalog.get(voice_key, {})
        desc = voice_info.get("description", "GENDER: Unknown - Check data file | TRAITS: Custom Profile Mapping")
        self.voice_desc_box.setText(desc)

    def _update_all_text_labels(self):
        self.lufs_val_label.setText(f"{self.lufs_slider.value() / 10.0:.1f} LUFS")
        self.peak_val_label.setText(f"{self.peak_slider.value() / 10.0:.1f} dB")
        self.tempo_val_label.setText(f"{self.tempo_slider.value() / 100.0:.2f}x")
        self.pitch_val_label.setText(f"{self.pitch_slider.value()} st")
        self.mix_val_label.setText(f"{self.mix_slider.value()}%")
        self.rate_val_label.setText(f"{self.rate_slider.value() / 100.0:.2f}")
        self.formant_val_label.setText(f"{self.formant_slider.value()}%")

    def _reset_to_saved_userconfig(self):
        self.log_signal.emit("Discarding changes... Reloading saved profile settings.")
        if self.config:
            config_dir = self.config.temp_wav_dir.parent.parent / "config"
            user_json_path = config_dir / "user_customization.json"
            if user_json_path.exists():
                try:
                    with open(user_json_path, "r", encoding="utf-8") as f:
                        self.config.user_customization = json.load(f)
                except Exception:
                    pass
            effects = self.config.user_customization.get("voice_effects", {})
            self._apply_raw_dictionary_to_sliders(effects)

    def _restore_factory_baselines(self):
        self.log_signal.emit("Restoring calibrated system baselines (-11.0 LUFS, 10% overlay)...")
        baseline_defaults = {
            "base_voice": self.voice_combo.currentText() or "af_heart",
            "loudness_target": -11.0,
            "loudness_true_peak": 6.0,
            "tempo": 1.00,
            "pitch_semitones": 0,
            "ring_mix": 10,
            "ring_freq": 300,
            "rate": 1.00,
            "formant_percent": 100,
            "enable_loudness": True,
            "enable_tempo": True,
            "enable_pitch": True,
            "enable_ring": True,
            "enable_rate": True,
            "enable_formant": True,
        }
        self._apply_raw_dictionary_to_sliders(baseline_defaults)

    def _on_character_preset_selected(self, chosen_preset):
        p = self.loaded_presets.get(chosen_preset)
        if not p:
            return

        for s in (self.lufs_slider, self.peak_slider, self.tempo_slider, self.pitch_slider, self.mix_slider, self.rate_slider, self.formant_slider):
            s.blockSignals(True)

        self._apply_raw_dictionary_to_sliders(p)

        for s in (self.lufs_slider, self.peak_slider, self.tempo_slider, self.pitch_slider, self.mix_slider, self.rate_slider, self.formant_slider):
            s.blockSignals(False)

        self._update_all_text_labels()
    @Slot(str)
    def _append_console_log(self, text):
        self.status_log_view.append(f">> {text}")
        self.status_log_view.ensureCursorVisible()

    @Slot(bool)
    def _set_button_lock_state(self, enabled):
        self.preview_btn.setEnabled(enabled)
        if hasattr(self, "preview_raw_btn"):
            self.preview_raw_btn.setEnabled(enabled)

    def _abort_active_wave_playback(self):
        import sys
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.log_signal.emit("Playback stopped.")

    def _trigger_async_preview_loop(self, raw_mode=False):
        self.preview_btn.setEnabled(False)
        self.preview_raw_btn.setEnabled(False)
        mode_label = "RAW UNMODIFIED" if raw_mode else "DSP PROCESSED"
        self.log_signal.emit(f"Initializing off-thread audio generator [{mode_label}]...")

        slider_parameters = {
            "raw_mode": raw_mode,
            "text": self.test_text_entry.text().strip(),
            "base_voice": self.voice_combo.currentText(),
            "loudness_target": round(self.lufs_slider.value() / 10.0, 1) if (self.loudness_toggle is not None and self.loudness_toggle.isChecked()) else -16.0,
            "loudness_true_peak": round(self.peak_slider.value() / 10.0, 1),
            "tempo": round(self.tempo_slider.value() / 100.0, 2) if (self.tempo_toggle is not None and self.tempo_toggle.isChecked()) else 1.0,
            "pitch_semitones": int(self.pitch_slider.value()) if (self.pitch_toggle is not None and self.pitch_toggle.isChecked()) else 0,
            "ring_mix": int(self.mix_slider.value()) if (self.mix_toggle is not None and self.mix_toggle.isChecked()) else 0,
            "rate": round(self.rate_slider.value() / 100.0, 2) if (self.rate_toggle is not None and self.rate_toggle.isChecked()) else 1.0,
            "ring_freq": getattr(self, "_active_ring_freq", 300),
            "formant_percent": int(self.formant_slider.value()) if (self.formant_toggle is not None and self.formant_toggle.isChecked()) else 100,
        }

        worker = threading.Thread(target=self._sound_generation_worker, args=(slider_parameters,), daemon=True)
        worker.start()

    def _sound_generation_worker(self, params):
        try:
            import onnxruntime as ort
            from kokoro_onnx import Kokoro
            dsp_module = importlib.import_module("pipeline.tts_utils")

            ort.set_default_logger_severity(3)
            processed_wav = self.config.temp_wav_dir / "sandbox_processed.wav"

            if isinstance(self.config.tts_model, Kokoro):
                tts = self.config.tts_model
            elif getattr(self.config, "kokoro_pipeline", None) is not None:
                tts = self.config.kokoro_pipeline
            else:
                model_path = self.config.tts_model
                voices_path = self.config.tts_voice_bin
                if not model_path.exists() or not voices_path.exists():
                    raise FileNotFoundError(f"Required weights files are missing at: {model_path} or {voices_path}")
                tts = Kokoro(str(model_path), str(voices_path))

            self.log_signal.emit(f"Synthesizing test line via Kokoro ({params['base_voice']})...")
            samples, sample_rate = tts.create(params["text"], voice=params["base_voice"], speed=1.0)
            audio = np.asarray(samples, dtype=np.float32)

            if not params.get("raw_mode", False):
                self.log_signal.emit("Applying DSP tuning chain & LUFS mastering...")
                audio = dsp_module.apply_vocal_dsp_chain_matrix(
                    audio=audio,
                    source_sr=int(sample_rate),
                    pitch_semitones=params["pitch_semitones"],
                    tempo=params["tempo"],
                    rate=params["rate"],
                    ring_freq=params["ring_freq"],
                    ring_mix=params["ring_mix"],
                    formant_percent=params["formant_percent"],
                    target_sr=48000,
                )
            else:
                self.log_signal.emit("Bypassing DSP modifiers for raw voice playback...")
                audio = dsp_module.apply_vocal_dsp_chain_matrix(
                    audio=audio,
                    source_sr=int(sample_rate),
                    pitch_semitones=0,
                    tempo=1.0,
                    rate=1.0,
                    ring_mix=0,
                    formant_percent=100,
                    target_sr=48000,
                )

            final_bytes = dsp_module.finalize_broadcast_audio(
                audio,
                loudness_target=params["loudness_target"],
                loudness_true_peak=params["loudness_true_peak"],
                sr=48000,
            )

            with wave.open(str(processed_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(final_bytes)

            self.log_signal.emit("Streaming preview audio to playback device...")
            import winsound
            winsound.PlaySound(str(processed_wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.log_signal.emit("Preview cycle finished.")
        except Exception as e:
            message = debug_error_message(e, "Generating an audio preview")
            self.log_signal.emit(f"ERROR: Preview pipeline aborted: {message}")
        finally:
            self.reset_btn_signal.emit(True)

    def showEvent(self, event):
        super().showEvent(event)
        active_bin = self.config.tts_voice_bin_name
        filtered = self._get_voices_for_bin(active_bin)

        if not filtered:
            print(f"[AUDIO PANEL WARNING] No voices matched active bin '{active_bin}'; showing full catalog.")
            filtered = list(self.voice_catalog.keys())

        raw_saved = (
            self.config.user_customization.get("voice_effects", {}).get("base_voice")
            if self.config
            else None
        )
        saved_voice = str(raw_saved) if raw_saved else ""

        if filtered != self.available_voices:
            current = self.voice_combo.currentText() or saved_voice
            self.available_voices = filtered
            self.voice_combo.blockSignals(True)
            self.voice_combo.clear()
            self.voice_combo.addItems(self.available_voices)
            if current and current in self.available_voices:
                self.voice_combo.setCurrentText(current)
            elif saved_voice and saved_voice in self.available_voices:
                self.voice_combo.setCurrentText(saved_voice)
            self.voice_combo.blockSignals(False)
            self._update_metadata_description_label(self.voice_combo.currentText())
        elif saved_voice and saved_voice in self.available_voices and self.voice_combo.currentText() != saved_voice:
            self.voice_combo.blockSignals(True)
            self.voice_combo.setCurrentText(saved_voice)
            self.voice_combo.blockSignals(False)
            self._update_metadata_description_label(saved_voice)

    def _get_voices_for_bin(self, active_bin: str) -> list[str]:
        matched = []
        for voice_id, meta in self.voice_catalog.items():
            bin_entry = meta.get("bin", [])
            if isinstance(bin_entry, list):
                if active_bin in bin_entry:
                    matched.append(voice_id)
            elif bin_entry == active_bin:
                matched.append(voice_id)
        return matched

    def gather_settings(self):
        if not self.config:
            return
        if "voice_effects" not in self.config.user_customization:
            self.config.user_customization["voice_effects"] = {}

        effects = self.config.user_customization["voice_effects"]
        effects["base_voice"] = self.voice_combo.currentText()
        effects["loudness_target"] = round(self.lufs_slider.value() / 10.0, 1)
        effects["loudness_true_peak"] = round(self.peak_slider.value() / 10.0, 1)
        effects["tempo"] = round(self.tempo_slider.value() / 100.0, 2)
        effects["pitch_semitones"] = self.pitch_slider.value()
        effects["ring_mix"] = self.mix_slider.value()
        effects["ring_freq"] = getattr(self, "_active_ring_freq", 300)
        effects["rate"] = round(self.rate_slider.value() / 100.0, 2)
        effects["formant_percent"] = self.formant_slider.value()

        effects["enable_loudness"] = self.loudness_toggle.isChecked() if self.loudness_toggle is not None else True
        effects["enable_tempo"] = self.tempo_toggle.isChecked() if self.tempo_toggle is not None else True
        effects["enable_pitch"] = self.pitch_toggle.isChecked() if self.pitch_toggle is not None else True
        effects["enable_ring"] = self.mix_toggle.isChecked() if self.mix_toggle is not None else True
        effects["enable_rate"] = self.rate_toggle.isChecked() if self.rate_toggle is not None else True
        effects["enable_formant"] = self.formant_toggle.isChecked() if self.formant_toggle is not None else True
