# manager/tabs/tab_system.py
import json
import csv
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys

class SystemTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.project_root = self.controller.project_root

        # Pull live definitions straight out of the parent's environment memory
        self.env_data = self.controller.env_data
        self.paths = self.env_data.get("paths", {})
        self.runtime = self.env_data.get("runtime", {})

        self._build_ui()

    def _build_ui(self):
        # Establish identical 960x748 balanced double-pane columns
        self.left_pane = ttk.Frame(self)
        self.left_pane.pack(side="left", fill="both", expand=True, padx=12, pady=5)

        self.right_pane = ttk.Frame(self)
        self.right_pane.pack(side="right", fill="both", expand=True, padx=12, pady=5)

        # ====================================================
        # LEFT PANE: STANDARD RUNTIME PIPELINE PATHS
        # ====================================================
        pipeline_group = ttk.LabelFrame(self.left_pane, text=" Core Platform File Infrastructure ", padding=12)
        pipeline_group.pack(fill="x", pady=5)

        # No Man's Sky Mod Path Tracker Input Box
        ttk.Label(pipeline_group, text="No Man's Sky Target Mod Directory:").pack(anchor="w", pady=2)
        path_frame = ttk.Frame(pipeline_group)
        path_frame.pack(fill="x", pady=5)

        self.mod_dir_var = tk.StringVar(value=self.paths.get("mod_dir", ""))
        self.controller.ui_vars["mod_dir"] = self.mod_dir_var

        self.mod_dir_entry = ttk.Entry(path_frame, textvariable=self.mod_dir_var, font=("TkDefaultFont", 10))
        self.mod_dir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Browse...", command=self._browse_mod_directory).pack(side="right", padx=6)
        ttk.Label(pipeline_group, text="↳ Points directly to your unpack tracking folder channel destination.", font=("TkDefaultFont", 8, "italic"), foreground="#888888").pack(anchor="w", pady=(0, 10))

        # ====================================================
        # EXOSUIT MAINTENANCE DECK (CACHE CONTROLS)
        # ====================================================
        maintenance_group = ttk.LabelFrame(self.left_pane, text=" Exosuit Core Maintenance Deck ", padding=12)
        maintenance_group.pack(fill="x", pady=10)

        # Cache Pre-Generation Button
        ttk.Label(maintenance_group, text="Background Cache Acceleration Matrix:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(2, 2))
        ttk.Label(maintenance_group, text="Pre-populates vocal waveform variations ahead of runtime loops.", font=("TkDefaultFont", 9, "italic")).pack(anchor="w", pady=(0, 6))

        self.topup_btn = ttk.Button(maintenance_group, text="Execute Cache Top-Up Sequence", command=self._run_async_topup)
        self.topup_btn.pack(anchor="w", pady=(0, 10))

        # Cache Purge Button
        ttk.Label(maintenance_group, text="Exosuit Storage Purge Protocols:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(5, 2))
        ttk.Label(maintenance_group, text="Clears temporary testing files and local sound caches cleanly.", font=("TkDefaultFont", 9, "italic")).pack(anchor="w", pady=(0, 6))

        self.purge_btn = ttk.Button(maintenance_group, text="Wipe Local Cached Wave Streams", command=self._purge_audio_cache)
        self.purge_btn.pack(anchor="w", pady=(0, 5))

        # Live Status Output Box
        self.status_label = ttk.Label(maintenance_group, text="Deck Systems Status: Idle", font=("TkDefaultFont", 10, "bold"), foreground="#002E00")
        self.status_label.pack(anchor="w", pady=(10, 2))

        # ====================================================
        # RIGHT PANE: THE STOVE BURNER DIAGNOSTIC VAULT
        # ====================================================
        vault_group = ttk.LabelFrame(self.right_pane, text=" Advanced Signal Diagnostics (Stove Burner Vault) ", padding=12)
        vault_group.pack(fill="both", expand=True, pady=5)

        # THE LEGENDARY WARN READOUT WELL
        warning_frame = ttk.LabelFrame(vault_group, text=" CRITICAL SYSTEM ADVISORY ")
        warning_frame.pack(fill="x", pady=(0, 10))

        warning_text = (
            "YOU TRULY DO NOT WANT TO DO THIS. But you cannot help but touch the hot stove burner.\n\n"
            "Very well. To open this panel, acknowledge that YOU UNDERSTAND CHANGING THESE SETTINGS COULD CAUSE "
            "UNINTENDED EFFECTS such as: complete mod failure, the total inability for your suit AI to tell Friend "
            "from Foe, severe semantic hallucinations from your local neural hulls, your domestic cat refusing to recognize "
            "you and aggressively hissing at your presence, every single left sock you own for the rest of your days vanishing "
            "from reality, and your tongue turning a very vivid (although highly interesting) shade of lavender.\n\n"
            "YOU TAKE FULL RESPONSIBILITY if your computer program programmatically purchases a heavy industrial snowblower "
            "from an online auction site and autonomously goes out into the street to chase teenagers celebrating their graduation."
        )

        warning_label = ttk.Label(warning_frame, text=warning_text, font=("TkDefaultFont", 9, "italic"), wraplength=400, justify="left", foreground="#4A0000")
        warning_label.pack(fill="x", padx=10, pady=10)

        # Interlocking Activation Checkbox matrix
        self.accept_responsibility_var = tk.BooleanVar(value=False)
        self.lock_checkbox = ttk.Checkbutton(vault_group, text="I ACCEPT ALL ULTIMATE RESPONSIBILITY AND TOUCH THE BURNER", variable=self.accept_responsibility_var, command=self._toggle_stove_burner_lock)
        self.lock_checkbox.pack(anchor="w", pady=5)

        # Advanced Settings Container Well (Disabled by default!)
        self.burner_well = ttk.Frame(vault_group)
        self.burner_well.pack(fill="both", expand=True, pady=10)

        # Cache-ahead boundary slider spinbox
        ttk.Label(self.burner_well, text="Exosuit Pre-Cache Max Threshold Horizon:").pack(anchor="w", pady=(5, 2))
        self.cache_max_var = tk.IntVar(value=self.runtime.get("quick_cache_max", 16))
        self.controller.ui_vars["quick_cache_max"] = self.cache_max_var
        self.cache_spin = ttk.Spinbox(self.burner_well, from_=1, to=64, increment=1, textvariable=self.cache_max_var, width=12, state="disabled")
        self.cache_spin.pack(anchor="w", pady=(0, 10))

        # Filesystem poll interval tick boundary slider
        ttk.Label(self.burner_well, text="Filesystem Scan Pool Tick Interval (Seconds):").pack(anchor="w", pady=(5, 2))
        self.interval_var = tk.DoubleVar(value=self.runtime.get("check_interval", 0.1))
        self.controller.ui_vars["check_interval"] = self.interval_var
        self.interval_spin = ttk.Spinbox(self.burner_well, from_=0.01, to=5.0, increment=0.05, textvariable=self.interval_var, width=12, state="disabled")
        self.interval_spin.pack(anchor="w", pady=(0, 5))

    # ====================================================
    # INTERACTIVE COMMAND OPERATIONS
    # ====================================================
    def _browse_mod_directory(self):
        chosen_dir = filedialog.askdirectory(initialdir=self.mod_dir_var.get())
        if chosen_dir:
            self.mod_dir_var.set(chosen_dir)

    def _toggle_stove_burner_lock(self):
        """Dynamic interlocking key: Unlocks the spin controls or traps the execution state."""
        if self.accept_responsibility_var.get():
            self.cache_spin.config(state="normal")
            self.interval_spin.config(state="normal")
            self.status_label.config(text="Deck Systems Status: ADVANCED BURNER MODES LIVE", foreground="#4A0000")
        else:
            self.cache_spin.config(state="disabled")
            self.interval_spin.config(state="disabled")
            self.status_label.config(text="Deck Systems Status: Idle", foreground="#002E00")

    def _purge_audio_cache(self):
        """Wipes the physical temporary wave directories clean from local drive sectors."""
        confirm = messagebox.askyesno("Confirm Purge", "Permanently erase all generated text-to-speech files sitting inside your local cache folder frames?")
        if not confirm:
            return

        try:
            cache_targets = [self.project_root / "cache"]
            for target in cache_targets:
                if target.exists():
                    # Clear individual files inside to preserve root path structures cleanly
                    for file in target.iterdir():
                        if file.is_file():
                            file.unlink()
            messagebox.showinfo("Success", "Exosuit local audio storage vectors purged flawlessly!")
            self.status_label.config(text="Deck Systems Status: Storage Purged Clean")
        except Exception as err:
            messagebox.showerror("Purge Error", f"Could not flush file boundaries: {err}")

    def _run_async_topup(self):
        self.topup_btn.config(state="disabled")
        self.status_label.config(text="Deck Systems Status: Loading ML Cache Accelerators...", foreground="#543B00")
        self.update_idletasks()
        threading.Thread(target=self._topup_worker_thread, daemon=True).start()

    def _topup_worker_thread(self):
        try:
            # Lazy load the configuration compilation assets internally to preserve 0s startup hooks
            from modular.config import SuitVoiceConfig
            from extras.cache_topup_to_max import fill_cache_for_ids

            self.status_label.config(text="Deck Systems Status: Pre-populating Cached Voice Sequences...", foreground="#543B00")
            self.update_idletasks()
            heavy_config = SuitVoiceConfig(init_llm=False)
            csv_path = heavy_config.csv_path
            wem_ids_to_topup = []
            if not csv_path or not csv_path.exists():
                raise FileNotFoundError(f"Intent map profile CSV path tracking missing: {csv_path}")
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Used", "").strip().lower() == "yes":
                        wem_ids_to_topup.append(row["WEM_number"])
                        # Map the exact max horizon slider number straight out of our form control spin box!
                        current_max_horizon = int(self.cache_max_var.get())
                        fill_cache_for_ids(wem_ids_to_topup, max_count=current_max_horizon)
                        messagebox.showinfo("Success", "Vocal variation buffer populating complete!")
        except Exception as e:
            messagebox.showerror("Error", f"Cache generation sequence encountered an issue: {e}")
        finally:
            self.topup_btn.config(state="normal")
            self.status_label.config(text="Deck Systems Status: Idle", foreground="#002E00")