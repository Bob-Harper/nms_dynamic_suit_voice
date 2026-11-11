# interface/panels/panel_3_audio.py
import json
import importlib
import threading
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox,
    QFrame, QPushButton, QLineEdit, QTextEdit
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

        self.available_voices = [
            "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
            "am_michael", "am_onyx", "am_puck", "am_santa",
            "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
            "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
            "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
            "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
        ]
        self.voice_metadata = {
            "am_adam": "GENDER: Male | TRAITS: Deep / Serious | QUALITY: Low (D) | GRADE: F+ (Exosuit Standard)",
            "am_echo": "GENDER: Male | TRAITS: Synthetic / Filtered | QUALITY: Med (C) | GRADE: D",
            "am_eric": "GENDER: Male | TRAITS: Flat / Computerised | QUALITY: Med (C) | GRADE: D",
            "am_fenrir": "GENDER: Male | TRAITS: Heavy / Industrial | QUALITY: High (B) | GRADE: C+",
            "am_liam": "GENDER: Male | TRAITS: Clear / Soft | QUALITY: Med (C) | GRADE: D",
            "am_michael": "GENDER: Male | TRAITS: Crisp / Articulate | QUALITY: High (B) | GRADE: C+",
            "am_onyx": "GENDER: Male | TRAITS: Low Pitch / Dark | QUALITY: Med (C) | GRADE: D",
            "am_puck": "GENDER: Male | TRAITS: Animated / Casual | QUALITY: High (B) | GRADE: C+",
            "am_santa": "GENDER: Male | TRAITS: Deep Accent / Heavy | QUALITY: Med (C) | GRADE: D-",
            "af_heart": "GENDER: Female | TRAITS: Warm / Affectionate | QUALITY: High (A) | GRADE: A",
            "af_alloy": "GENDER: Female | TRAITS: Cold / Metallic | QUALITY: High (B) | GRADE: C",
            "af_aoede": "GENDER: Female | TRAITS: Melodic / Smooth | QUALITY: High (B) | GRADE: C+",
            "af_bella": "GENDER: Female | TRAITS: Expressive / Bright | QUALITY: High (A) | GRADE: A-",
            "af_jessica": "GENDER: Female | TRAITS: Casual / Conversational | QUALITY: Low (C) | GRADE: D",
            "af_kore": "GENDER: Female | TRAITS: Sharp / Clear | QUALITY: High (B) | GRADE: C+",
            "af_nicole": "GENDER: Female | TRAITS: Studio / Crisp | QUALITY: High (B) | GRADE: B-",
            "af_nova": "GENDER: Female | TRAITS: Direct / Robotic | QUALITY: High (B) | GRADE: C",
            "af_river": "GENDER: Female | TRAITS: Soft / Muffled | QUALITY: Low (C) | GRADE: D",
            "af_sarah": "GENDER: Female | TRAITS: Standard Technical | QUALITY: High (B) | GRADE: C+",
            "af_sky": "GENDER: Female | TRAITS: Light / Airy | QUALITY: High (B) | GRADE: C-",
            "bf_alice": "GENDER: Female (UK) | TRAITS: Precise Dialect | QUALITY: Low (C) | GRADE: D",
            "bf_emma": "GENDER: Female (UK) | TRAITS: Structured / Professional | QUALITY: High (B) | GRADE: B-",
            "bf_isabella": "GENDER: Female (UK) | TRAITS: Polished Technical | QUALITY: High (B) | GRADE: C",
            "bf_lily": "GENDER: Female (UK) | TRAITS: Soft Accent | QUALITY: Low (C) | GRADE: D",
            "bm_daniel": "GENDER: Male (UK) | TRAITS: Clear Dialect | QUALITY: Low (C) | GRADE: D",
            "bm_fable": "GENDER: Male (UK) | TRAITS: Cinematic Narrative | QUALITY: High (B) | GRADE: C",
            "bm_george": "GENDER: Male (UK) | TRAITS: Heavy Corporate | QUALITY: High (B) | GRADE: C",
            "bm_lewis": "GENDER: Male (UK) | TRAITS: Command Executive | QUALITY: Low (C) | GRADE: D+"
        }

        self._build_ui()
        self._initialize_data_fields()
    def _build_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setSpacing(15)
        master_layout.setContentsMargins(15, 15, 15, 15)

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        preset_group = QWidget()
        preset_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setContentsMargins(15, 15, 15, 15)
        preset_layout.setSpacing(12)

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
        self.voice_desc_box.setWordWrap(True) # FIXED: Forces long profile notes to wrap to multi-line smoothly
        self.voice_desc_box.setStyleSheet("""
            QLabel { background-color: #0c0c0e; border: 1px dashed #1f2430; color: #5c6773;
                     padding: 6px; font-family: 'Consolas', monospace; font-size: 11px; border-radius: 4px; }
        """)
        preset_layout.addWidget(self.voice_desc_box)
        left_layout.addWidget(preset_group)

        primary_group = QWidget()
        primary_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        primary_layout = QVBoxLayout(primary_group)
        primary_layout.setContentsMargins(15, 15, 15, 15)
        primary_layout.setSpacing(15)
        primary_header = QLabel("PRIMARY EXOSUIT AUDIO TUNING")
        primary_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        primary_layout.addWidget(primary_header)

        self.gain_slider, self.gain_val_label = self._create_slider_row(primary_layout, "Vocal Volume Boost (dB Gain) [Baseline: 5]:", -10, 25, 5, self._on_slider_changed)
        self.tempo_slider, self.tempo_val_label = self._create_slider_row(primary_layout, "Sentence Pacing (Speech Speed) [Baseline: 1.00]:", 50, 200, 100, self._on_slider_changed)
        self.pitch_slider, self.pitch_val_label = self._create_slider_row(primary_layout, "Core Voice Tone (Pitch Shift) [Baseline: 4]:", -12, 12, 4, self._on_slider_changed)
        self.mix_slider, self.mix_val_label = self._create_slider_row(primary_layout, "Synthetic Cybernetic Overlay % [Baseline: 100]:", 0, 100, 100, self._on_slider_changed)
        left_layout.addWidget(primary_group)
        advanced_group = QWidget()
        advanced_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setContentsMargins(15, 15, 15, 15)
        advanced_layout.setSpacing(15)
        advanced_header = QLabel("ADVANCED SIGNAL DIAGNOSTICS (FINE TUNING)")
        advanced_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        advanced_layout.addWidget(advanced_header)

        self.rate_slider, self.rate_val_label = self._create_slider_row(advanced_layout, "Audio Frequency Warp (Chipmunk Scalar) [Baseline: 0.50]:", 10, 150, 50, self._on_slider_changed)
        self.freq_slider, self.freq_val_label = self._create_slider_row(advanced_layout, "Modulation Carrier Wave Frequency (Hz) [Baseline: 300]:", 50, 1000, 300, self._on_slider_changed)
        self.formant_slider, self.formant_val_label = self._create_slider_row(advanced_layout, "Vocal Resonator Bandwidth (Throat Size %) [Baseline: 80]:", 10, 150, 80, self._on_slider_changed)

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
        self.preview_btn.clicked.connect(self._trigger_async_preview_loop)

        self.stop_playback_btn = QPushButton("STOP PLAYBACK")
        self.stop_playback_btn.setStyleSheet("""
            QPushButton { background-color: #880000; border: 1px solid #ff3333; color: white; padding: 10px 14px; font-weight: bold; font-family: 'Consolas', monospace; }
            QPushButton:hover { background-color: #aa0000; border-color: #ff5555; }
        """)
        self.stop_playback_btn.clicked.connect(self._abort_active_wave_playback)

        playback_action_row.addWidget(self.preview_btn, stretch=2)
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
    def _create_slider_row(self, parent_layout, label_text, min_val, max_val, default_val, change_callback):
        row_frame = QWidget()
        row_frame.setStyleSheet("border: none; background: transparent;")
        row_frame_layout = QHBoxLayout(row_frame)
        row_frame_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(label_text)
        title_label.setMinimumWidth(260)
        title_label.setStyleSheet("color: #ffffff; font-size: 11px;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #1f2430; height: 6px; background: #0c0c0e; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffaa00; border: 1px solid #ffaa00; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }
            QSlider::handle:horizontal:hover { background: #ffffff; border-color: #ffaa00; }
        """)
        slider.valueChanged.connect(change_callback)

        val_label = QLabel(str(default_val))
        val_label.setFixedWidth(50)
        val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_label.setStyleSheet("font-family: 'Consolas', monospace; color: #ffaa00; font-weight: bold; font-size: 11px;")

        row_frame_layout.addWidget(title_label)
        row_frame_layout.addWidget(slider, stretch=1)
        row_frame_layout.addWidget(val_label)

        parent_layout.addWidget(row_frame)
        return slider, val_label

    def _initialize_data_fields(self):
        if not self.config or "voice_effects" not in self.config.user_customization:
            return
        effects = self.config.user_customization.get("voice_effects", {})
        self._apply_raw_dictionary_to_sliders(effects)

    def _apply_raw_dictionary_to_sliders(self, data_dict):
        active_voice = data_dict.get("base_voice", "am_adam")
        if active_voice in self.available_voices:
            self.voice_combo.setCurrentText(active_voice)
            self._update_metadata_description_label(active_voice)

        self.gain_slider.setValue(int(data_dict.get("gain_db", 5)))
        self.tempo_slider.setValue(int(float(data_dict.get("tempo", 1.02)) * 100))
        self.pitch_slider.setValue(int(data_dict.get("pitch_semitones", 4)))
        self.mix_slider.setValue(int(data_dict.get("ring_mix", 100)))
        self.rate_slider.setValue(int(float(data_dict.get("rate", 0.51)) * 100))
        self.freq_slider.setValue(int(data_dict.get("ring_freq", 300)))
        self.formant_slider.setValue(int(data_dict.get("formant_percent", 80)))
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
        desc = self.voice_metadata.get(voice_key, "GENDER: Unknown | TRAITS: Custom Profile Mapping")
        self.voice_desc_box.setText(desc)

    def _update_all_text_labels(self):
        self.gain_val_label.setText(f"{self.gain_slider.value()} dB")
        self.tempo_val_label.setText(f"{self.tempo_slider.value() / 100.0:.2f}x")
        self.pitch_val_label.setText(f"{self.pitch_slider.value()} st")
        self.mix_val_label.setText(f"{self.mix_slider.value()}%")
        self.rate_val_label.setText(f"{self.rate_slider.value() / 100.0:.2f}")
        self.freq_val_label.setText(f"{self.freq_slider.value()} Hz")
        self.formant_val_label.setText(f"{self.formant_slider.value()}%")

    def _reset_to_saved_userconfig(self):
        self.log_signal.emit("Discarding changes... Reloading current configuration profile vectors.")
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
        self.log_signal.emit("Flushing parameters... Snapping sliders to factory system baselines.")
        factory_defaults = {
            "base_voice": "am_adam",
            "gain_db": 5,
            "tempo": 1.00,
            "pitch_semitones": 4,
            "ring_mix": 100,
            "rate": 0.50,
            "ring_freq": 300,
            "formant_percent": 80
        }
        self._apply_raw_dictionary_to_sliders(factory_defaults)
    def _on_character_preset_selected(self, chosen_preset):
        p = self.loaded_presets.get(chosen_preset)
        if not p:
            return
        self.gain_slider.blockSignals(True)
        self.tempo_slider.blockSignals(True)
        self.pitch_slider.blockSignals(True)
        self.mix_slider.blockSignals(True)
        self.rate_slider.blockSignals(True)
        self.freq_slider.blockSignals(True)
        self.formant_slider.blockSignals(True)

        self.gain_slider.setValue(int(p.get("gain_db", 5)))
        self.tempo_slider.setValue(int(float(p.get("tempo", 1.02)) * 100))
        self.pitch_slider.setValue(int(p.get("pitch_semitones", 4)))
        self.mix_slider.setValue(int(p.get("ring_mix", 100)))
        self.rate_slider.setValue(int(float(p.get("rate", 0.51)) * 100))
        self.freq_slider.setValue(int(p.get("ring_freq", 300)))
        self.formant_slider.setValue(int(p.get("formant_percent", 80)))

        self.gain_slider.blockSignals(False)
        self.tempo_slider.blockSignals(False)
        self.pitch_slider.blockSignals(False)
        self.mix_slider.blockSignals(False)
        self.rate_slider.blockSignals(False)
        self.freq_slider.blockSignals(False)
        self.formant_slider.blockSignals(False)

        if "base_voice" in p and p["base_voice"] in self.available_voices:
            self.voice_combo.setCurrentText(p["base_voice"])

        self._update_all_text_labels()

    @Slot(str)
    def _append_console_log(self, text):
        self.status_log_view.append(f">> {text}")
        self.status_log_view.ensureCursorVisible()

    @Slot(bool)
    def _set_button_lock_state(self, enabled):
        self.preview_btn.setEnabled(enabled)

    def _abort_active_wave_playback(self):
        import sys
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.log_signal.emit("Playback process aborted by user directive.")

    def _trigger_async_preview_loop(self):
        self.preview_btn.setEnabled(False)
        self.log_signal.emit("Initializing off-thread matrix audio generator...")

        slider_parameters = {
            "text": self.test_text_entry.text().strip(),
            "base_voice": self.voice_combo.currentText(),
            "gain_db": float(self.gain_slider.value()),
            "tempo": round(self.tempo_slider.value() / 100.0, 2),
            "pitch_semitones": int(self.pitch_slider.value()),
            "ring_mix": int(self.mix_slider.value()),
            "rate": round(self.rate_slider.value() / 100.0, 2),
            "ring_freq": int(self.freq_slider.value()),
            "formant_percent": int(self.formant_slider.value())
        }

        worker = threading.Thread(target=self._sound_generation_worker, args=(slider_parameters,), daemon=True)
        worker.start()
    def _sound_generation_worker(self, params):
        try:
            import sys
            import onnxruntime as ort
            dsp_module = importlib.import_module("pipeline.tts_utils")

            ort.set_default_logger_severity(3)
            self.log_signal.emit("Connecting to pipeline matrix parameters...")

            processed_wav = self.config.temp_wav_dir / "sandbox_processed.wav"

            self.log_signal.emit("Instantiating voice model weights from local cache...")
            from kokoro_onnx import Kokoro

            models_cfg = self.config.environment.get("models", {})
            active_model_name = models_cfg.get("tts_model", "kokoro-v1.0.fp16.onnx")

            project_root = self.config.temp_wav_dir.parent.parent
            weights_dir = project_root / "assets" / "weights"
            model_path = weights_dir / active_model_name

            if "zh" in str(model_path):
                voices_path = weights_dir / "voices-v1.1-zh.bin"
            else:
                voices_path = weights_dir / "voices-v1.0.bin"

            if not model_path.exists() or not voices_path.exists():
                raise FileNotFoundError(f"Required weights files are missing at: {model_path} or {voices_path}")

            tts = Kokoro(str(model_path), str(voices_path))

            self.log_signal.emit(f"Synthesizing raw test wave forms via Kokoro ({params['base_voice']})...")
            samples, sample_rate = tts.create(params["text"], voice=params["base_voice"], speed=1.0)

            import numpy as np
            audio = np.array(samples, dtype=np.float32)

            self.log_signal.emit("Injecting local NumPy robotic matrix overlay...")
            audio = dsp_module.apply_vocal_dsp_chain_matrix(
                audio=audio,
                source_sr=sample_rate,
                gain_db=params["gain_db"],
                pitch_semitones=params["pitch_semitones"],
                tempo=params["tempo"],
                rate=params["rate"],
                ring_freq=params["ring_freq"],
                ring_mix=params["ring_mix"],
                formant_percent=params["formant_percent"],
                target_sr=44100,
                apply_gain_stage=False
            )

            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))

            amplitude_multiplier = 10 ** (params["gain_db"] / 20.0)
            audio = audio * amplitude_multiplier * 32767
            audio = np.clip(audio, -32768, 32767)
            final_bytes = audio.astype(np.int16).tobytes()

            import wave
            with wave.open(str(processed_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(final_bytes)

            self.log_signal.emit("Audio calculation complete! Streaming to device...")
            import winsound

            # FIXED: Bitwise OR attaches the non-blocking worker flag to allow instant cancellation
            winsound.PlaySound(str(processed_wav), winsound.SND_FILENAME | winsound.SND_ASYNC)

            self.log_signal.emit("Preview cycle finished successfully.")
        except Exception as e:
            message = debug_error_message(e, "Generating an audio preview")
            self.log_signal.emit(f"ERROR: Preview pipeline aborted: {message}")
        finally:
            self.reset_btn_signal.emit(True)


    def gather_settings(self):
        if not self.config:
            return
        if "voice_effects" not in self.config.user_customization:
            self.config.user_customization["voice_effects"] = {}

        effects = self.config.user_customization["voice_effects"]
        effects["base_voice"] = self.voice_combo.currentText()
        effects["gain_db"] = self.gain_slider.value()
        effects["tempo"] = round(self.tempo_slider.value() / 100.0, 2)
        effects["pitch_semitones"] = self.pitch_slider.value()
        effects["ring_mix"] = self.mix_slider.value()
        effects["rate"] = round(self.rate_slider.value() / 100.0, 2)
        effects["ring_freq"] = self.freq_slider.value()
        effects["formant_percent"] = self.formant_slider.value()
