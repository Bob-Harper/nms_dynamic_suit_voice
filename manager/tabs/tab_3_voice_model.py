# manager/tabs/tab_voice_model.py
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
import sys
from manager.tooltip import bind_tooltip


class VoiceModelTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.project_root = self.controller.project_root

        # ====================================================
        # AUTHORITATIVE 8-MODEL CORE ROSTER
        # ====================================================
        self.model_catalog = {
            "tts_models/en/ek1/tacotron2": {
                "name": "Tacotron2 EK1", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Vintage-themed synthetic engine. Great for classic old-school terminal styles."
            },
            "tts_models/en/ljspeech/tacotron2-DDC": {
                "name": "Tacotron2 DDC", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "A highly stable, traditional technical voice layer with excellent clarity."
            },
            "tts_models/en/ljspeech/tacotron2-DCA": {
                "name": "Tacotron2 DCA", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Crisp navigational vocal structure. Provides crisp, distinct alert profiles."
            },
            "tts_models/en/ljspeech/tacotron2-DDC_ph": {
                "name": "Tacotron2 DDC PH (Mod Default)", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "The original baseline fine-tuned vocal core. Natively optimized for real-time play."
            },
            "tts_models/en/ljspeech/glow-tts": {
                "name": "Glow TTS Engine", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Smooth phrasing layout. Exceptional baseline for applying heavy MALE SHIFT profiles!"
            },
            "tts_models/en/ljspeech/speedy-speech": {
                "name": "Speedy Speech Matrix", "gender": "FEMALE", "pacing": "Relaxed (0.60 - 0.75)",
                "note": "Extremely fast output engine. Drop sentence pacing significantly to ensure clarity."
            },
            "tts_models/en/ljspeech/fast_pitch": {
                "name": "Fast Pitch Core", "gender": "FEMALE", "pacing": "Standard (1.00)",
                "note": "Energetic, modern synthesis model. Delivers prominent high-tech status readouts."
            },
            "tts_models/en/jenny/jenny": {
                "name": "Jenny (Conversational AI)", "gender": "FEMALE", "pacing": "Relaxed (0.80 - 0.90)",
                "note": "Highly organic natural speech footprint. Best paired with the Clinical Matrix preset."
            }
        }

        self.list_index_keys = list(self.model_catalog.keys())
        self._build_ui()

    def _build_ui(self):
        self.left_pane = ttk.Frame(self)
        self.left_pane.pack(side="left", fill="both", expand=True, padx=12, pady=5)

        self.right_pane = ttk.Frame(self)
        self.right_pane.pack(side="right", fill="both", expand=True, padx=12, pady=5)

        # LEFT PANE: INSTALLED MODEL CATALOG LIST
        list_container = ttk.LabelFrame(self.left_pane, text=" Available Exosuit Speech Engines ", padding=12)
        list_container.pack(fill="both", expand=True, pady=5)

        ttk.Label(list_container, text="Select Active Synthesis Model:").pack(anchor="w", pady=2)

        self.model_listbox = tk.Listbox(list_container, height=12, font=("TkDefaultFont", 10), selectmode="browse")
        self.model_listbox.pack(fill="both", expand=True, pady=5)
        self.model_listbox.bind("<<ListboxSelect>>", self._on_model_selection_change)

        # Model Action Controls
        self.action_frame = ttk.Frame(list_container)
        self.action_frame.pack(fill="x", side="bottom", pady=5)

        self.apply_btn = ttk.Button(self.action_frame, text="Set as Active Model", command=self._activate_selected_model, state="disabled")
        self.apply_btn.pack(side="left", padx=2)

        self.download_btn = ttk.Button(self.action_frame, text="Download Assets", command=self._trigger_async_download, state="disabled")
        self.download_btn.pack(side="left", padx=2)

        self.delete_btn = ttk.Button(self.action_frame, text="Uninstall Model", command=self._uninstall_model_assets, state="disabled")
        self.delete_btn.pack(side="left", padx=2)

        # RIGHT PANE: DESCRIPTIVE DETAILS PANEL
        self.details_container = ttk.LabelFrame(self.right_pane, text=" Engine Specifics & System Diagnostics ", padding=12)
        self.details_container.pack(fill="both", expand=True, pady=5)

        self.meta_title_label = ttk.Label(self.details_container, text="No Engine Selected", font=("TkDefaultFont", 11, "bold"))
        self.meta_title_label.pack(anchor="w", pady=(0, 10))

        self.meta_status_label = ttk.Label(self.details_container, text="Status: Ready", font=("TkDefaultFont", 10, "bold"), foreground="#4A5568")
        self.meta_status_label.pack(anchor="w", pady=2)

        self.meta_desc_label = ttk.Label(self.details_container, text="Select an engine from the list layout to adjust active suit weights.", font=("TkDefaultFont", 9, "italic"), wraplength=380, justify="left")
        self.meta_desc_label.pack(fill="x", pady=10)

        self.download_progress_label = ttk.Label(self.details_container, text="Download Queue: Idle", font=("Consolas", 9), foreground="#2D3748")
        self.download_progress_label.pack(side="bottom", anchor="w", pady=5)

        # Trigger initial data print on boot up
        self._refresh_catalog_list_display()

    def _refresh_catalog_list_display(self):
        self.model_listbox.delete(0, tk.END)

        # Resolve active selection priority
        current_active = self.controller.user_data.get("tts_model")
        if not current_active:
            with open(self.controller.env_config_file, "r", encoding="utf-8") as f:
                env_map = json.load(f)
            current_active = env_map.get("models", {}).get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")

        # Synchronize mailroom box mapping state
        if "tts_model" not in self.controller.ui_vars:
            self.controller.ui_vars["tts_model"] = tk.StringVar(value=current_active)
        else:
            self.controller.ui_vars["tts_model"].set(current_active)

        for key in self.list_index_keys:
            info = self.model_catalog[key]
            is_downloaded = self._check_if_model_present_on_disk(key)

            status_tag = "[Downloaded]" if is_downloaded else "[Available]"
            if key == current_active:
                status_tag = "▶ [ACTIVE ON EXOSUIT]"

            self.model_listbox.insert(tk.END, f" {status_tag} {info['name']}")

    def _check_if_model_present_on_disk(self, model_key: str) -> bool:
        local_appdata_path = Path.home() / "AppData" / "Local" / "tts"
        folder_name = model_key.replace("/", "--")
        target_folder = local_appdata_path / folder_name
        return target_folder.exists() and any(target_folder.iterdir())

    def _on_model_selection_change(self, event=None):
        selection = self.model_listbox.curselection()
        if not selection:
            return

        selected_index = selection[0]
        self.selected_model_key = self.list_index_keys[selected_index]
        info = self.model_catalog[self.selected_model_key]

        is_downloaded = self._check_if_model_present_on_disk(self.selected_model_key)

        self.meta_title_label.config(text=info["name"])

        # Format descriptive text layout from hardcoded dictionary cards
        detailed_profile_text = (
            f"• Full Identifier Key:\n  {self.selected_model_key}\n\n"
            f"• Vocal Baseline Profile: [{info['gender']}]\n"
            f"• Recommended Pacing Bounds: {info['pacing']}\n\n"
            f"• Exosuit Tuning Note:\n  {info['note']}"
        )
        self.meta_desc_label.config(text=detailed_profile_text)

        # Extract true active profile from controller data layers
        current_active = self.controller.user_data.get("tts_model")
        if not current_active:
            with open(self.controller.env_config_file, "r", encoding="utf-8") as f:
                env_map = json.load(f)
            current_active = env_map.get("models", {}).get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph")

        is_active = (current_active == self.selected_model_key)

        if is_active:
            self.meta_status_label.config(text="Status: Active and Loaded on Exosuit Matrix", foreground="#002E00")
            self.apply_btn.config(state="disabled")
            self.download_btn.config(state="disabled")
            self.delete_btn.config(state="disabled")
        elif is_downloaded:
            self.meta_status_label.config(text="Status: Offline Asset Present on Local Disk", foreground="#543B00")
            self.apply_btn.config(state="normal")
            self.download_btn.config(state="disabled")
            self.delete_btn.config(state="normal")
        else:
            self.meta_status_label.config(text="Status: Not Downloaded (Assets Missing)", foreground="#4A0000")
            self.apply_btn.config(state="disabled")
            self.download_btn.config(state="normal")
            self.delete_btn.config(state="disabled")

    def _activate_selected_model(self):
        try:
            if self.controller.user_config_file.exists():
                with open(self.controller.user_config_file, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
            else:
                user_data = {}

            user_data["tts_model"] = self.selected_model_key

            with open(self.controller.user_config_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)

            self.controller.user_data = user_data

            if "tts_model" in self.controller.ui_vars:
                self.controller.ui_vars["tts_model"].set(self.selected_model_key)

            # Fire the continuous save routine to keep the app active and update the listbox visuals
            self.controller.save_and_continue_settings()

            # 6. REFRESH ACTIVE LAYOUT DISPLAYS ON SCREEN
            self._refresh_catalog_list_display()
            self._on_model_selection_change()

        except Exception as e:
            messagebox.showerror("Configuration Error", f"Could not preserve target voice choice: {e}")

    def _uninstall_model_assets(self):
        confirm = messagebox.askyesno("Confirm Deletion", f"Permanently uninstall local files for:\n{self.model_catalog[self.selected_model_key]['name']}?\n\nThis will clear up space from your system storage.")
        if not confirm:
            return

        try:
            import shutil
            local_appdata_path = Path.home() / "AppData" / "Local" / "tts"
            folder_name = self.selected_model_key.replace("/", "--")
            target_folder = local_appdata_path / folder_name

            if target_folder.exists():
                shutil.rmtree(target_folder)

            messagebox.showinfo("Success", "Model weights cleared out of system storage cleanly.")
            self._refresh_catalog_list_display()
            self._on_model_selection_change()
        except Exception as e:
            messagebox.showerror("Purge Failure", f"Could not remove local folder modules: {e}")

    def _trigger_async_download(self):
        self.download_btn.config(state="disabled")
        self.download_progress_label.config(text="Queue Status: Fetching background weights tracker...")
        threading.Thread(target=self._download_worker_thread, daemon=True).start()

    def _download_worker_thread(self):
        try:
            from TTS.api import TTS
            self.download_progress_label.config(text="Queue Status: Downloading engine binary weights (Please wait)...")
            _warmed_engine = TTS(model_name=self.selected_model_key)
            self.download_progress_label.config(text="Queue Status: Model downloaded successfully.")
            messagebox.showinfo("Success", f"Voice engine parameters compiled and verified safely on your drive.")
            self.controller.root.after(0, self._refresh_catalog_list_display)
        except Exception as e:
            self.download_progress_label.config(text="Queue Status: Download process failed.")
            messagebox.showerror("Network Error", f"Vocal package download sequence encountered an issue:\n{e}")
        finally:
            self.controller.root.after(0, self._on_model_selection_change)
