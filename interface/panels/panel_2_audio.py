# interface/panels/panel_2_audio.py
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
    # Dynamic thread safe status macro callback signals
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

        # Connect internal signal handling loops safely across thread boundaries
        self.log_signal.connect(self._append_console_log)
        self.reset_btn_signal.connect(self._set_button_lock_state)

        self._build_ui()
        self._initialize_data_fields()

    def _build_ui(self):
        # Master Horizontal Splitter Layout Container
        master_layout = QHBoxLayout(self)
        master_layout.setSpacing(15)
        master_layout.setContentsMargins(15, 15, 15, 15)

        # LEFT PANE: TUNING CONTROLS MATRIX
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Profiles
        preset_group = QWidget()
        preset_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setContentsMargins(15, 15, 15, 15)
        preset_header = QLabel("QUICK EXOSUIT CHARACTER PROFILES")
        preset_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
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
        preset_layout.addWidget(preset_header)
        preset_layout.addLayout(preset_row)
        left_layout.addWidget(preset_group)

        # Primary Sliders
        primary_group = QWidget()
        primary_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        primary_layout = QVBoxLayout(primary_group)
        primary_layout.setContentsMargins(15, 15, 15, 15)
        primary_layout.setSpacing(15)
        primary_header = QLabel("PRIMARY EXOSUIT AUDIO TUNING")
        primary_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        primary_layout.addWidget(primary_header)

        self.gain_slider, self.gain_val_label = self._create_slider_row(primary_layout, "Vocal Volume Boost (dB Gain) [Baseline: 5]:", -10, 20, 5, self._on_slider_changed)
        self.tempo_slider, self.tempo_val_label = self._create_slider_row(primary_layout, "Sentence Pacing (Speech Speed) [Baseline: 1.00]:", 50, 200, 100, self._on_slider_changed)
        self.pitch_slider, self.pitch_val_label = self._create_slider_row(primary_layout, "Core Voice Tone (Pitch Shift) [Baseline: 4]:", -12, 12, 4, self._on_slider_changed)
        self.mix_slider, self.mix_val_label = self._create_slider_row(primary_layout, "Synthetic Cybernetic Overlay % [Baseline: 100]:", 0, 100, 100, self._on_slider_changed)
        left_layout.addWidget(primary_group)

        # Advanced Sliders
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
        left_layout.addWidget(advanced_group, stretch=1)
        master_layout.addWidget(left_pane, stretch=1)

        # RIGHT PANE: REAL-TIME SYNTHESIS SANDBOX SIMULATOR
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

        self.preview_btn = QPushButton("APPLY EFFECTS & PLAY PREVIEW")
        self.preview_btn.setStyleSheet("""
            QPushButton { background-color: #005588; border: 1px solid #00aaff; color: white; padding: 10px 20px; font-weight: bold; font-family: 'Consolas', monospace; }
            QPushButton:hover { background-color: #007acc; border-color: #33bbff; }
            QPushButton:disabled { background-color: #222225; border-color: #444448; color: #66666d; }
        """)
        self.preview_btn.clicked.connect(self._trigger_async_preview_loop)
        sandbox_layout.addWidget(self.preview_btn)

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
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 0, 0, 0)

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

        row_layout.addWidget(title_label)
        row_layout.addWidget(slider, stretch=1)
        row_layout.addWidget(val_label)

        parent_layout.addWidget(row_frame)
        return slider, val_label

    def _initialize_data_fields(self):
        if not self.config or "voice_effects" not in self.config.user_customization:
            return
        effects = self.config.user_customization.get("voice_effects", {})
        self.gain_slider.setValue(int(effects.get("gain_db", 5)))
        self.tempo_slider.setValue(int(float(effects.get("tempo", 1.02)) * 100))
        self.pitch_slider.setValue(int(effects.get("pitch_semitones", 4)))
        self.mix_slider.setValue(int(effects.get("ring_mix", 100)))
        self.rate_slider.setValue(int(float(effects.get("rate", 0.50)) * 100))
        self.freq_slider.setValue(int(effects.get("ring_freq", 300)))
        self.formant_slider.setValue(int(effects.get("formant_percent", 80)))
        self._update_all_text_labels()

    def _on_slider_changed(self, value):
        self._update_all_text_labels()
        if self.preset_combo.currentIndex() != 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)

    def _update_all_text_labels(self):
        self.gain_val_label.setText(f"{self.gain_slider.value()} dB")
        self.tempo_val_label.setText(f"{self.tempo_slider.value() / 100.0:.2f}x")
        self.pitch_val_label.setText(f"{self.pitch_slider.value()} st")
        self.mix_val_label.setText(f"{self.mix_slider.value()}%")
        self.rate_val_label.setText(f"{self.rate_slider.value() / 100.0:.2f}")
        self.freq_val_label.setText(f"{self.freq_slider.value()} Hz")
        self.formant_val_label.setText(f"{self.formant_slider.value()}%")

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
        self.rate_slider.setValue(int(float(p.get("rate", 0.50)) * 100))
        self.freq_slider.setValue(int(p.get("ring_freq", 300)))
        self.formant_slider.setValue(int(p.get("formant_percent", 80)))

        self.gain_slider.blockSignals(False)
        self.tempo_slider.blockSignals(False)
        self.pitch_slider.blockSignals(False)
        self.mix_slider.blockSignals(False)
        self.rate_slider.blockSignals(False)
        self.freq_slider.blockSignals(False)
        self.formant_slider.blockSignals(False)
        self._update_all_text_labels()

    # ==============================================================================
    # ASYNCHRONOUS SOUND PREVIEW SIMULATOR MATRIX HANDLERS
    # ==============================================================================
    @Slot(str)
    def _append_console_log(self, text):
        self.status_log_view.append(f">> {text}")
        self.status_log_view.ensureCursorVisible()

    @Slot(bool)
    def _set_button_lock_state(self, enabled):
        self.preview_btn.setEnabled(enabled)

    def _trigger_async_preview_loop(self):
        """Spins up a detached worker thread to run speech processing away from the UI."""
        self.preview_btn.setEnabled(False)
        self.log_signal.emit("Initializing off-thread matrix audio generator...")

        slider_parameters = {
            "text": self.test_text_entry.text().strip(),
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
        """Isolated off-thread background loop executing dynamic math voice transformation."""
        try:
            import sys
            # LAZY DEFERRED PIPELINE IMPORTS: Kept inside the function loop context boundary
            config_module = importlib.import_module("pipeline.config")
            dsp_module = importlib.import_module("pipeline.tts_utils")

            self.log_signal.emit("Connecting to pipeline matrix parameters...")
            preview_cfg = config_module.SuitVoiceConfig(init_llm=False)

            project_root = Path(__file__).resolve().parents[2]
            cache_root_value = self.config.environment.get("paths", {}).get(
                "cache_root", "cache"
            )
            cache_root = Path(cache_root_value)
            if not cache_root.is_absolute():
                cache_root = project_root / cache_root
            cache_root.mkdir(parents=True, exist_ok=True)

            raw_wav = cache_root / "sandbox_raw.wav"
            processed_wav = cache_root / "sandbox_processed.wav"

            self.log_signal.emit("Instantiating voice model weights from local cache...")
            from TTS.api import TTS

            active_model = self.config.user_customization.get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")
            tts = TTS(model_name=active_model)
            tts.to("cpu")

            self.log_signal.emit("Synthesizing raw test wave forms...")
            tts.tts_to_file(text=params["text"], file_path=str(raw_wav))

            self.log_signal.emit("Injecting local NumPy robotic matrix overlay...")
            dsp_module.apply_vocal_dsp_chain(
                config=preview_cfg,
                input_wav=raw_wav,
                output_wav=processed_wav,
                gain_db=params["gain_db"],
                pitch_semitones=params["pitch_semitones"],
                tempo=params["tempo"],
                rate=params["rate"],
                ring_freq=params["ring_freq"],
                ring_mix=params["ring_mix"],
                formant_percent=params["formant_percent"],
                target_sr=44100
            )

            self.log_signal.emit("Audio calculation complete! Streaming to device...")
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(str(processed_wav), winsound.SND_FILENAME)
            else:
                import os
                os.system(f"aplay {processed_wav}" if sys.platform == "linux" else f"afplay {processed_wav}")

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
        effects["gain_db"] = self.gain_slider.value()
        effects["tempo"] = round(self.tempo_slider.value() / 100.0, 2)
        effects["pitch_semitones"] = self.pitch_slider.value()
        effects["ring_mix"] = self.mix_slider.value()
        effects["rate"] = round(self.rate_slider.value() / 100.0, 2)
        effects["ring_freq"] = self.freq_slider.value()
        effects["formant_percent"] = self.formant_slider.value()
