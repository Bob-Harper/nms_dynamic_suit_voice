# manager/tabs/tab_audio.py - JSON-Driven Character Presets
import json
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
from pathlib import Path
import sys
from manager.tooltip import bind_tooltip


class AudioTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.effects_data = self.controller.user_data.get("voice_effects", {})

        # DYNAMIC PRESET PARSING: Load character data configurations straight from disk
        self.presets_file = self.controller.project_root / "data" / "audio_presets.json"
        self.loaded_presets = {}
        self.preset_options = ["Browse Custom Voice Signatures..."]

        if self.presets_file.exists():
            try:
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    self.loaded_presets = json.load(f)
                self.preset_options.extend(list(self.loaded_presets.keys()))
            except Exception as e:
                print(f"Preset Loader: Failed to parse audio_presets.json: {e}")

        self._build_ui()

    def _build_ui(self):
        self.left_pane = ttk.Frame(self)
        self.left_pane.pack(side="left", fill="both", expand=True, padx=12, pady=5)

        self.right_pane = ttk.Frame(self)
        self.right_pane.pack(side="right", fill="both", expand=True, padx=12, pady=5)

        # Quick Exosuit Character Profiles Panel
        presets_container = ttk.LabelFrame(self.left_pane, text=" Quick Exosuit Character Profiles ", padding=12)
        presets_container.pack(fill="x", pady=5)

        ttk.Label(presets_container, text="Precalibrated Vocal Signatures:").pack(anchor="w", pady=2)

        # COMBOBOX OPTIONS ARE NOW LOADED DYNAMICALLY FROM DISK KEYS!
        self.character_preset_var = tk.StringVar(value="Browse Available Voice Signatures...")
        self.preset_combo = ttk.Combobox(
            presets_container,
            textvariable=self.character_preset_var,
            values=self.preset_options,
            state="readonly",
            width=45
        )
        self.preset_combo.pack(anchor="w", pady=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_character_preset_selected)

        # SECTION 1: PRIMARY USER CONTROLS (BEST RESULTS)
        primary_group = ttk.LabelFrame(self.left_pane, text=" Primary Exosuit Audio Tuning ", padding=12)
        primary_group.pack(fill="x", pady=5)

        # Volume Boost
        ttk.Label(primary_group, text="Vocal Volume Boost (dB Gain) [Baseline: 5]:").pack(anchor="w", pady=(2, 0))
        self.gain_scale = tk.Scale(primary_group, from_=-10, to=20, orient="horizontal", resolution=1, length=280, highlightthickness=0)
        self.gain_scale.set(self.effects_data.get("gain_db", 5))
        self.gain_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["gain_db"] = self.gain_scale
        bind_tooltip([self.gain_scale], "If the voice seems too quiet within the game, increase the Gain value.  Higher values can increase distortion.")

        # Sentence Pacing
        ttk.Label(primary_group, text="Sentence Pacing (Speech Speed) [Baseline: 1.00]:").pack(anchor="w", pady=(5, 0))
        self.tempo_scale = tk.Scale(primary_group, from_=0.5, to=2.0, orient="horizontal", resolution=0.01, length=280, highlightthickness=0)
        self.tempo_scale.set(self.effects_data.get("tempo", 1.02))
        self.tempo_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["tempo"] = self.tempo_scale
        bind_tooltip([self.tempo_scale], "Adjust the pace of the synthesized voice without affecting the pitch.")

        # Core Voice Tone
        ttk.Label(primary_group, text="Core Voice Tone (Pitch & Speed Shift) [Baseline: 4]:").pack(anchor="w", pady=(5, 0))
        self.pitch_scale = tk.Scale(primary_group, from_=-12, to=12, orient="horizontal", resolution=1, length=280, highlightthickness=0)
        self.pitch_scale.set(self.effects_data.get("pitch_semitones", 4))
        self.pitch_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["pitch_semitones"] = self.pitch_scale
        bind_tooltip([self.pitch_scale], "Adjusts the vocal pitch up or down without changing the speed.")

        # Synthetic Cybernetic Overlay
        ttk.Label(primary_group, text="Synthetic Cybernetic Overlay % [Baseline: 100]:").pack(anchor="w", pady=(5, 0))
        self.mix_scale = tk.Scale(primary_group, from_=0, to=100, orient="horizontal", resolution=5, length=280, highlightthickness=0)
        self.mix_scale.set(self.effects_data.get("ring_mix", 100))
        self.mix_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["ring_mix"] = self.mix_scale
        bind_tooltip([self.mix_scale], "Blend unprocessed audio with post-processed audio: 0% is no postprocessing effects at all, 100% is full robotic style distortion.")

        # SECTION 2: ADVANCED SIGNAL DIAGNOSTICS (FINE TUNING)
        advanced_group = ttk.LabelFrame(self.left_pane, text=" Advanced Signal Diagnostics (Fine Tuning) ", padding=12)
        advanced_group.pack(fill="x", pady=10)

        # Audio Frequency Warp
        ttk.Label(advanced_group, text="Audio Frequency Warp (Chipmunk Scalar) [Baseline: 0.50]:").pack(anchor="w", pady=(2, 0))
        self.rate_scale = tk.Scale(advanced_group, from_=0.1, to=1.5, orient="horizontal", resolution=0.01, length=280, highlightthickness=0)
        self.rate_scale.set(self.effects_data.get("rate", 0.50))
        self.rate_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["rate"] = self.rate_scale
        bind_tooltip([self.rate_scale], "Alters pitch and speed simultaneously (aka Chipmunk effect). Acts as an additional distortion layer over the vocal baseline.")

        # Modulation Carrier Wave Frequency
        ttk.Label(advanced_group, text="Modulation Carrier Wave Frequency (Hz) [Baseline: 300]:").pack(anchor="w", pady=(5, 0))
        self.freq_scale = tk.Scale(advanced_group, from_=50, to=1000, orient="horizontal", resolution=10, length=280, highlightthickness=0)
        self.freq_scale.set(self.effects_data.get("ring_freq", 300))
        self.freq_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["ring_freq"] = self.freq_scale
        bind_tooltip([self.freq_scale], "Adjust the frequency of the Robotic distortion effect.  To remove it completely, set the Synthetic Cybernetic Overlay to 0.")

        # Vocal Resonator Bandwidth
        ttk.Label(advanced_group, text="Vocal Resonator Bandwidth (Throat Size %) [Baseline: 80]:").pack(anchor="w", pady=(5, 0))
        self.formant_scale = tk.Scale(advanced_group, from_=10, to=150, orient="horizontal", resolution=5, length=280, highlightthickness=0)
        self.formant_scale.set(self.effects_data.get("formant_percent", 80))
        self.formant_percent_var = self.formant_scale
        self.formant_scale.pack(anchor="w", pady=(0, 5))
        self.controller.ui_vars["formant_percent"] = self.formant_scale
        bind_tooltip([self.formant_scale], "Adjust how deep/gravelly the voice sounds.")

        # ====================================================
        # RIGHT PANE: LIVE SANDBOX SIMULATOR
        # ====================================================
        sandbox_container = ttk.LabelFrame(self.right_pane, text=" Real-Time Synthesis Sandbox ", padding=12)
        sandbox_container.pack(fill="both", expand=True, pady=5)

        warning_frame = ttk.LabelFrame(sandbox_container, text=" EXOSUIT TUNING ADVISORY ")
        warning_frame.pack(fill="x", pady=(0, 10))

        warning_text = (
            "• INITIALIZATION PAUSE:\n"
            "  When you click 'Apply Effects' in a session, the utility may take a minute or more"
            "  to boot the local speech model into memory.\n\n"
            "• ALTERNATE VOICE MODELS:\n"
            "  Selecting a new voice model may require a network download to pull the file if not already present. Swapping will pause the manager until the model is loaded to memory.\n\n"
            "  These models are installed, uninstalled, and managed through the Voice Model tab."
        )

        warning_label = ttk.Label(warning_frame, text=warning_text, font=("TkDefaultFont", 9, "italic"), wraplength=380, justify="left")
        warning_label.pack(fill="x", padx=10, pady=10)

        ttk.Label(sandbox_container, text="Input Live Diagnostic Test Phrase:").pack(anchor="w", pady=2)
        self.test_text_box = tk.Text(sandbox_container, height=4, width=38, font=("TkDefaultFont", 10))
        self.test_text_box.insert("1.0", "This is a test of how the Dynamic Suit Voice will sound in the game.")
        self.test_text_box.pack(fill="x", pady=5)

        self.generate_btn = ttk.Button(sandbox_container, text="Apply Effects & Play Audio", command=self.run_async_audio_test)
        self.generate_btn.pack(fill="x", pady=5)

        ttk.Label(sandbox_container, text="Tuning Engine Pipeline Output:").pack(anchor="w", pady=(10, 2))
        self.status_log = tk.Text(sandbox_container, height=8, width=38, bg="#121212", fg="#00FF00", font=("Consolas", 9))
        self.status_log.pack(fill="both", expand=True, pady=5)
        self.update_log_display(" TTO Engine Status: Idle\n Ready to synthesize testing streams.")

        ttk.Button(self.right_pane, text="Reset Page to Sane Defaults", command=self.reset_to_sane_defaults).pack(anchor="e", pady=5)

    # ====================================================
    # OPERATIONAL DATA HANDLERS
    # ====================================================
    def _on_character_preset_selected(self, event=None):
        """Extracts JSON parameters dynamically and checks compatibility bounds."""
        chosen = self.character_preset_var.get()
        p = self.loaded_presets.get(chosen)

        if p:
            # 1. MODEL COMPATIBILITY RECOGNITION LOCK
            current_model = self.controller.user_data.get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")
            target_model = p.get("target_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")

            if current_model != target_model:
                messagebox.showwarning(
                    "Tuning Calibration Advisory",
                    "Notice: These character presets were handcrafted specifically for the default Mod Voice Engine.\n\n"
                    "When running an alternative voice model, these slider numbers may sound fast, slow, or distorted until you manually adjust them."
                )

            # 2. MAP SETTINGS TO GUI SLIDERS GENERIPALLY FROM JSON KEY-VALUES!
            self.gain_scale.set(p.get("gain_db", 5))
            self.pitch_scale.set(p.get("pitch_semitones", 4))
            self.tempo_scale.set(p.get("tempo", 1.02))
            self.rate_scale.set(p.get("rate", 0.50))
            self.freq_scale.set(p.get("ring_freq", 300))
            self.mix_scale.set(p.get("ring_mix", 100))
            self.formant_scale.set(p.get("formant_percent", 80))

            self.update_log_display(f" {p.get('description', 'Preset loaded.')}")

    def update_log_display(self, text_message: str, append=False):
        self.status_log.config(state="normal")
        if not append:
            self.status_log.delete("1.0", tk.END)
        self.status_log.insert("end", text_message + "\n")
        self.status_log.see("end")
        self.status_log.config(state="disabled")

    def reset_to_sane_defaults(self):
        self.gain_scale.set(5)
        self.pitch_scale.set(4)
        self.tempo_scale.set(1.02)
        self.rate_scale.set(0.50)
        self.freq_scale.set(300)
        self.mix_scale.set(100)
        self.formant_scale.set(80)
        self.update_log_display(" Matrix reset cleanly to factory defaults.")

    def run_async_audio_test(self):
        self.generate_btn.config(state="disabled")
        self.update_log_display(" Starting background voice synthesis sequence...")
        threading.Thread(target=self.audio_generation_worker, daemon=True).start()

    def audio_generation_worker(self):
        try:
            from modular.config import SuitVoiceConfig
            from TTS.api import TTS
            import numpy as np
            import soundfile as sf
            from scipy.signal import resample

            self.update_log_display(" Connecting to Coqui TTS Engine...")
            heavy_cfg = SuitVoiceConfig(init_llm=False)

            embeds_dir = self.controller.project_root / "cache"
            embeds_dir.mkdir(parents=True, exist_ok=True)

            temp_wav = embeds_dir / "sandbox_raw.wav"
            final_wav = embeds_dir / "sandbox_processed.wav"

            text_payload = self.test_text_box.get("1.0", tk.END).strip()

            gain_val = int(self.gain_scale.get())
            pitch_semitones = int(self.pitch_scale.get())
            tempo_val = float(self.tempo_scale.get())
            rate_val = float(self.rate_scale.get())
            ring_freq = int(self.freq_scale.get())
            ring_mix = int(self.mix_scale.get())
            formant_percent = int(self.formant_scale.get())

            # Read user configurations directly out of the controller's active live memory cache first!
            model_signature = self.controller.user_data.get("tts_model")

            # If the user customization envelope doesn't hold a custom choice yet, fall back to base system weights
            if not model_signature:
                with open(self.controller.env_config_file, "r", encoding="utf-8") as f:
                    env_map = json.load(f)
                model_signature = env_map.get("models", {}).get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")

            self.update_log_display(f" Instantiating weights -> {model_signature}", append=True)
            tts_engine = TTS(model_name=model_signature)
            tts_engine.to("cpu")

            self.update_log_display(f" Instantiating weights -> {model_signature}", append=True)
            tts_engine = TTS(model_name=model_signature)
            tts_engine.to("cpu")

            self.update_log_display(" Synthesizing vocal wave footprints...", append=True)
            tts_engine.tts_to_file(text=text_payload, file_path=str(temp_wav))

            self.update_log_display(" Injecting authentic local numpy robotic filter matrices...", append=True)
            audio, sr = sf.read(str(temp_wav))
            MIN_SAMPLES = 1000

            # A. Pitch Adjustment Resample Loop
            factor_pitch = 2 ** (pitch_semitones / 12)
            n_samples_pitch = max(int(len(audio) / factor_pitch), MIN_SAMPLES)
            audio = resample(audio, n_samples_pitch)

            # B. Throat Formant Resonance Resample Loop
            factor_formant = formant_percent / 100
            n_samples_formant = max(int(len(audio) / factor_formant), MIN_SAMPLES)
            audio = resample(audio, n_samples_formant)

            # C. Hardware Ring Modulation (Wet/Dry Blend)
            wet_factor = ring_mix / 100.0
            dry_factor = 1.0 - wet_factor

            dry_signal = audio.copy()
            t = np.arange(len(audio)) / sr
            wet_signal = audio * np.sin(2 * np.pi * ring_freq * t)

            audio = (dry_signal * dry_factor) + (wet_signal * wet_factor)
            sf.write(str(final_wav), audio, sr)

            self.update_log_display(" Applying volume and tempo layers via FFmpeg...", append=True)
            CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
            setrate_val = int(44100 * rate_val)
            filter_string = f"volume={gain_val}dB,atempo={tempo_val},asetrate={setrate_val}"

            subprocess.run([
                "ffmpeg", "-hide_banner", "-y",
                "-i", str(final_wav),
                "-af", filter_string,
                str(temp_wav)
            ], check=True, creationflags=CREATE_NO_WINDOW)

            self.update_log_display(" Footprints generated successfully! Triggering playback stream...", append=True)
            subprocess.run([
                "ffplay", "-nodisp", "-autoexit", str(temp_wav)
            ], check=True, creationflags=CREATE_NO_WINDOW)

            self.update_log_display("\n Playback loop finished smoothly. Tuning complete.")

        except Exception as e:
            self.update_log_display(f"\n ERROR: Synthesis pipeline failed:\n {e}")
            messagebox.showerror("Sandbox Failure", f"Vocal processing chain error:\n{e}")
        finally:
            self.generate_btn.config(state="normal")
