# manager/dsv_manager.py
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys
import warnings
import importlib

warnings.filterwarnings("ignore", category=UserWarning, module="jieba")

project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class DSVManagementUtility:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NMS Dynamic Suit Voice - Management Utility")
        self.root.geometry("960x820")
        self.root.minsize(580, 440)
        self.project_root = project_root

        self.env_config_file = self.project_root / "config" / "environment_config.json"
        self.user_config_file = self.project_root / "config" / "user_customization.json"

        # Central memory registers for the plug-and-play architecture
        self.ui_vars = {}
        self.active_tabs = {}

        self.load_raw_configurations()

        # Dynamic Notebook Canvas mounting grid
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # --------------------------------------------------
        # THE CORE DISK SCANNER LOOP (100% FUTUREPROOFED)
        # --------------------------------------------------
        self.discover_and_mount_tabs()

        # Action Buttons Tray
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(fill="x", side="bottom", padx=10, pady=10)

        self.save_continue_btn = ttk.Button(self.button_frame, text="Apply Changes", command=self.save_and_continue_settings)
        self.save_continue_btn.pack(side="right", padx=5)

        self.save_close_btn = ttk.Button(self.button_frame, text="Save & Close", command=self.save_and_close_settings)
        self.save_close_btn.pack(side="right", padx=5)

        self.cancel_btn = ttk.Button(self.button_frame, text="Cancel", command=self.root.quit)
        self.cancel_btn.pack(side="right", padx=5)

    def discover_and_mount_tabs(self):
        """Sweeps manager/tabs/ recursively, sorting automatically by number."""
        tabs_dir = Path(__file__).parent / "tabs"
        if not tabs_dir.exists():
            return

        # 1. Grab files and let Python sort them naturally by their new numbered prefixes
        scanned_files = list(tabs_dir.glob("tab_*.py"))
        scanned_files.sort()

        for file_path in scanned_files:
            module_name = file_path.stem  # e.g., 'tab_1_profile' or 'tab_2_audio'
            try:
                # Dynamically import the module
                imported_module = importlib.import_module(f"manager.tabs.{module_name}")

                # 2. Extract words while ignoring 'tab' and any ordering numbers!
                # Filters out things that are purely numbers so they don't break class naming
                words = [w for w in module_name.split('_')[1:] if not w.isdigit()]

                # e.g., 'tab_1_profile' still perfectly derives 'ProfileTab'
                class_name = "".join(w.capitalize() for w in words) + "Tab"
                tab_class = getattr(imported_module, class_name, None)

                if tab_class:
                    display_title = " ".join(w.capitalize() for w in words)
                    title_overrides = {
                        "Profile": "User Profile",
                        "Audio": "Audio Modifiers",
                        "System": "System Environment",
                        "Voice Model": "Voice Model"
                    }
                    display_title = title_overrides.get(display_title, display_title)

                    tab_instance = tab_class(self.notebook, self)
                    self.notebook.add(tab_instance, text=display_title)
                    self.active_tabs[display_title] = tab_instance
            except Exception as load_err:
                print(f"Dynamic numbered mount error on '{module_name}': {load_err}")

    def load_raw_configurations(self):
        try:
            with open(self.env_config_file, "r", encoding="utf-8") as f:
                self.env_data = json.load(f)
            if self.user_config_file.exists():
                with open(self.user_config_file, "r", encoding="utf-8") as f:
                    self.user_data = json.load(f)
            else:
                self.user_data = {}

            self.prompt_data_file = self.project_root / "data" / "prompt_data.json"
            if self.prompt_data_file.exists():
                with open(self.prompt_data_file, "r", encoding="utf-8") as f:
                    p_structures = json.load(f)
                self.available_tones = list(p_structures.get("tones", {}).keys())
                self.available_wordiness = list(p_structures.get("wordiness", {}).keys())
            else:
                self.available_tones = ["Standard"]
                self.available_wordiness = ["Standard"]
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Could not read platform files:\n{e}")
            sys.exit(1)

    def save_and_continue_settings(self):
        """Assembles variables and writes to disk while keeping the control window open."""
        self._execute_file_save_matrix()
        # Update the local user data memory cache so other tabs inherit the fresh values instantly!
        if self.user_config_file.exists():
            with open(self.user_config_file, "r", encoding="utf-8") as f:
                self.user_data = json.load(f)
        messagebox.showinfo("Applied", "Preferences committed safely to disk! Control panel remaining active.")

    def save_and_close_settings(self):
        """Assembles variables, writes to disk, and closes the entire management application."""
        self._execute_file_save_matrix()
        messagebox.showinfo("Success", "Custom configurations saved flawlessly! Restart the system tray to apply.")
        self.root.destroy()

    def _execute_file_save_matrix(self):
        """The core internal database writing loop that compiles all layout variables to files."""
        # This contains your working JSON writer block from earlier
        updated_customization = {
            "tts_model": str(self.ui_vars.get("tts_model", tk.StringVar(value=self.user_data.get("tts_model", "tts_models/en/ljspeech/tacotron2-DDC_ph"))).get()),
            "player_name": str(self.ui_vars.get("player_name", tk.StringVar(value="Interloper")).get()),
            "phrase_settings": {
                "tone": str(self.ui_vars.get("tone", tk.StringVar(value="Standard")).get()),
                "wordiness": str(self.ui_vars.get("wordiness", tk.StringVar(value="Standard")).get())
            },
            "voice_effects": {
                "gain_db": int(self.ui_vars.get("gain_db", tk.IntVar(value=5)).get()),
                "pitch_semitones": int(self.ui_vars.get("pitch_semitones", tk.IntVar(value=4)).get()),
                "tempo": float(self.ui_vars.get("tempo", tk.DoubleVar(value=1.02)).get()),
                "rate": float(self.ui_vars.get("rate", tk.DoubleVar(value=0.51)).get()),
                "ring_freq": int(self.ui_vars.get("ring_freq", tk.IntVar(value=300)).get()),
                "ring_mix": int(self.ui_vars.get("ring_mix", tk.IntVar(value=100)).get()),
                "formant_percent": int(self.ui_vars.get("formant_percent", tk.IntVar(value=80)).get())
            }
        }
        # Extract platform directory variables safely out of memory maps
        mod_dir_val = self.ui_vars.get("mod_dir")
        if mod_dir_val:
            self.env_data["paths"]["mod_dir"] = str(mod_dir_val.get())

        interval_val = self.ui_vars.get("check_interval")
        if interval_val:
            self.env_data["runtime"]["check_interval"] = float(interval_val.get())

        cache_max_val = self.ui_vars.get("quick_cache_max")
        if cache_max_val:
            self.env_data["runtime"]["quick_cache_max"] = int(cache_max_val.get())

        with open(self.env_config_file, "w", encoding="utf-8") as f:
            json.dump(self.env_data, f, indent=4)
        with open(self.user_config_file, "w", encoding="utf-8") as f:
            json.dump(updated_customization, f, indent=4)

        mod_dir_val = self.ui_vars.get("mod_dir")
        if mod_dir_val:
            self.env_data["paths"]["mod_dir"] = str(mod_dir_val.get())

        interval_val = self.ui_vars.get("check_interval")
        if interval_val:
            self.env_data["runtime"]["check_interval"] = float(interval_val.get())

        with open(self.env_config_file, "w", encoding="utf-8") as f:
            json.dump(self.env_data, f, indent=4)


if __name__ == "__main__":
    app_root = tk.Tk()
    app = DSVManagementUtility(app_root)
    app_root.mainloop()
