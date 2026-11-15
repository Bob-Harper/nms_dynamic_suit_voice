# interface/panels/panel_3_audio.py
import json
import importlib
import threading
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox,
    QFrame, QPushButton, QLineEdit, QTextEdit, QCheckBox
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

        # Pull voice catalog and active voice bin from SuitVoiceConfig
        self.voice_catalog = self.config.ttm_voices_data
        self.available_voices = self._get_voices_for_bin(self.config.tts_voice_bin_name)
        self.voice_catalog = self.config.ttm_voices_data
        active_bin = self.config.tts_voice_bin_name

        # Filter voices to match the currently selected voice bin
        self.available_voices = [
            voice_id for voice_id, meta in self.voice_catalog.items()
            if meta.get("bin") == active_bin
        ]

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
        self.voice_desc_box.setWordWrap(True) # FIXED: Forces long profile notes to wrap to multi-line
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

        self.gain_slider, self.gain_val_label, self.gain_toggle = self._create_slider_row(primary_layout, "Vocal Volume Boost (dB Gain) [Baseline: 5]:", -10, 25, 5, self._on_slider_changed)
        self.tempo_slider, self.tempo_val_label, self.tempo_toggle = self._create_slider_row(primary_layout, "Sentence Pacing (Speech Speed) [Baseline: 1.00]:", 50, 200, 100, self._on_slider_changed)
        self.pitch_slider, self.pitch_val_label, self.pitch_toggle = self._create_slider_row(primary_layout, "Core Voice Tone (Pitch Shift) [Baseline: 4]:", -12, 12, 4, self._on_slider_changed)
        self.mix_slider, self.mix_val_label, self.mix_toggle = self._create_slider_row(primary_layout, "Synthetic Cybernetic Overlay % [Baseline: 100]:", 0, 100, 100, self._on_slider_changed)

        left_layout.addWidget(primary_group)
        advanced_group = QWidget()
        advanced_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setContentsMargins(15, 15, 15, 15)
        advanced_layout.setSpacing(15)
        advanced_header = QLabel("ADVANCED SIGNAL DIAGNOSTICS (FINE TUNING)")
        advanced_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        advanced_layout.addWidget(advanced_header)

        self.rate_slider, self.rate_val_label, self.rate_toggle = self._create_slider_row(advanced_layout, "Audio Frequency Warp (Chipmunk Scalar) [Baseline: 0.50]:", 10, 150, 50, self._on_slider_changed)
        self.freq_slider, self.freq_val_label, _ = self._create_slider_row(advanced_layout, "Modulation Carrier Wave Frequency (Hz) [Baseline: 300]:", 50, 1000, 300, self._on_slider_changed, has_toggle=False)
        self.formant_slider, self.formant_val_label, self.formant_toggle = self._create_slider_row(advanced_layout, "Vocal Resonator Bandwidth (Throat Size %) [Baseline: 80]:", 10, 150, 80, self._on_slider_changed)

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
            toggle_box.setToolTip("Enable or bypass this audio effect")
            toggle_box.setStyleSheet("""
                QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #ffaa00; border-radius: 3px; background: #0c0c0e; }
                QCheckBox::indicator:checked { background: #ffaa00; }
            """)
            row_frame_layout.addWidget(toggle_box)

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
            QSlider::handle:horizontal:disabled { background: #4b5668; border-color: #4b5668; }
        """)
        slider.valueChanged.connect(change_callback)

        val_label = QLabel(str(default_val))
        val_label.setFixedWidth(50)
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

        self.gain_slider.setValue(int(data_dict.get("gain_db")))
        self.tempo_slider.setValue(int(float(data_dict.get("tempo")) * 100))
        self.pitch_slider.setValue(int(data_dict.get("pitch_semitones")))
        self.mix_slider.setValue(int(data_dict.get("ring_mix")))
        self.rate_slider.setValue(int(float(data_dict.get("rate")) * 100))
        self.freq_slider.setValue(int(data_dict.get("ring_freq")))
        self.formant_slider.setValue(int(data_dict.get("formant_percent")))
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
        factory_defaults = self.config.default_customization.get("voice_effects", {})
        if not factory_defaults:
            print("[AUDIO PANEL WARNING] voice_effects missing from default_customization.json; using fallback values.")
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
        if hasattr(self, "preview_raw_btn"):
            self.preview_raw_btn.setEnabled(enabled)

    def _abort_active_wave_playback(self):
        import sys
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.log_signal.emit("Playback process aborted by user directive.")

    def _trigger_async_preview_loop(self, raw_mode=False):
        self.preview_btn.setEnabled(False)
        self.preview_raw_btn.setEnabled(False)
        mode_label = "RAW UNMODIFIED" if raw_mode else "DSP PROCESSED"
        self.log_signal.emit(f"Initializing off-thread audio generator [{mode_label}]...")

        slider_parameters = {
            "raw_mode": raw_mode,
            "text": self.test_text_entry.text().strip(),
            "base_voice": self.voice_combo.currentText(),
            "gain_db": float(self.gain_slider.value()) if (self.gain_toggle is not None and self.gain_toggle.isChecked()) else 0.0,
            "tempo": round(self.tempo_slider.value() / 100.0, 2) if (self.tempo_toggle is not None and self.tempo_toggle.isChecked()) else 1.0,
            "pitch_semitones": int(self.pitch_slider.value()) if (self.pitch_toggle is not None and self.pitch_toggle.isChecked()) else 0,
            "ring_mix": int(self.mix_slider.value()) if (self.mix_toggle is not None and self.mix_toggle.isChecked()) else 0,
            "rate": round(self.rate_slider.value() / 100.0, 2) if (self.rate_toggle is not None and self.rate_toggle.isChecked()) else 1.0,
            "ring_freq": int(self.freq_slider.value()),
            "formant_percent": int(self.formant_slider.value()) if (self.formant_toggle is not None and self.formant_toggle.isChecked()) else 100
        }

        worker = threading.Thread(target=self._sound_generation_worker, args=(slider_parameters,), daemon=True)
        worker.start()

    def _sound_generation_worker(self, params):
        try:
            import onnxruntime as ort
            dsp_module = importlib.import_module("pipeline.tts_utils")

            ort.set_default_logger_severity(3)
            self.log_signal.emit("Connecting to pipeline matrix parameters...")

            processed_wav = self.config.temp_wav_dir / "sandbox_processed.wav"

            self.log_signal.emit("Instantiating voice model weights from local cache...")
            from kokoro_onnx import Kokoro

            model_path = self.config.tts_model
            voices_path = self.config.tts_voice_bin

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

    def showEvent(self, event):
        super().showEvent(event)
        active_bin = self.config.tts_voice_bin_name
        filtered = self._get_voices_for_bin(active_bin)

        if not filtered:
            print(f"[AUDIO PANEL WARNING] No voices matched active bin '{active_bin}'; showing full catalog.")
            filtered = list(self.voice_catalog.keys())

        if filtered != self.available_voices:
            current = self.voice_combo.currentText()
            self.available_voices = filtered
            self.voice_combo.blockSignals(True)
            self.voice_combo.clear()
            self.voice_combo.addItems(self.available_voices)
            if current in self.available_voices:
                self.voice_combo.setCurrentText(current)
            self.voice_combo.blockSignals(False)
            self._update_metadata_description_label(self.voice_combo.currentText())

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
        effects["gain_db"] = self.gain_slider.value()
        effects["tempo"] = round(self.tempo_slider.value() / 100.0, 2)
        effects["pitch_semitones"] = self.pitch_slider.value()
        effects["ring_mix"] = self.mix_slider.value()
        effects["rate"] = round(self.rate_slider.value() / 100.0, 2)
        effects["ring_freq"] = self.freq_slider.value()
        effects["formant_percent"] = self.formant_slider.value()
