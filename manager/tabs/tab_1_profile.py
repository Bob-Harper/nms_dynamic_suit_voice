# manager/tabs/tab_1_profile.py
import tkinter as tk
from tkinter import ttk
import json
from manager.tooltip import bind_tooltip

class ProfileTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        phrase_settings = self.controller.user_data.get("phrase_settings", {})

        # ====================================================
        # PANEL 1: ITERATION IDENTITY REGISTRATION (TOP PANEL)
        # ====================================================
        identity_container = ttk.LabelFrame(self, text=" Iteration Identity Registration ", padding=15)
        identity_container.pack(fill="x", padx=10, pady=10)

        # Track name variables using our mailroom mapping dictionary arrays
        player_name_var = tk.StringVar(value=self.controller.user_data.get("player_name", "Interloper"))
        self.controller.ui_vars["player_name"] = player_name_var

        ttk.Label(identity_container, text="Iteration Name:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(identity_container, textvariable=player_name_var, width=30)
        self.name_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # ====================================================
        # PANEL 2: EXOSUIT CORE SYSTEM BRIEFING (CENTER MAIN)
        # ====================================================
        self.briefing_container = ttk.LabelFrame(self, text=" Exosuit Core System Briefing ", padding=15)
        self.briefing_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Dynamic variable mapping arrays to handle live greeting refreshes
        self.welcome_label = ttk.Label(self.briefing_container, text="", font=("TkDefaultFont", 10), wraplength=780, justify="left")
        self.welcome_label.pack(fill="both", expand=True, padx=5, pady=5)

        # INTERLOCKING EVENT TRACER (THE ON-CHANGE LISTENER!)
        # This forces the interface to fire the update text macro instantly on every single keystroke
        player_name_var.trace_add("write", self._on_iteration_name_changed)

        # ====================================================
        # PANEL 3: COMPANION PREFERENCES (BOTTOM PANEL)
        # ====================================================
        prefs_container = ttk.LabelFrame(self, text=" Companion Preferences ", padding=15)
        prefs_container.pack(fill="x", side="bottom", padx=10, pady=10)

        # Tone Selection Setup
        tone_var = tk.StringVar(value=phrase_settings.get("tone", "Standard"))
        self.controller.ui_vars["tone"] = tone_var

        ttk.Label(prefs_container, text="Companion AI Tone Profile:").grid(row=0, column=0, sticky="w", pady=4)
        self.tone_combo = ttk.Combobox(prefs_container, textvariable=tone_var, values=self.controller.available_tones, state="readonly", width=27)
        self.tone_combo.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        self.tone_desc_label = ttk.Label(prefs_container, text="", font=("TkDefaultFont", 9, "italic"), wraplength=450, justify="left")
        self.tone_desc_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 6))

        # Wordiness Selection Setup
        wordiness_var = tk.StringVar(value=phrase_settings.get("wordiness", "Standard"))
        self.controller.ui_vars["wordiness"] = wordiness_var

        ttk.Label(prefs_container, text="Companion AI Verbiage Style:").grid(row=2, column=0, sticky="w", pady=4)
        self.wordiness_combo = ttk.Combobox(prefs_container, textvariable=wordiness_var, values=self.controller.available_wordiness, state="readonly", width=27)
        self.wordiness_combo.grid(row=2, column=1, sticky="w", padx=10, pady=4)

        self.wordiness_desc_label = ttk.Label(prefs_container, text="", font=("TkDefaultFont", 9, "italic"), wraplength=450, justify="left")
        self.wordiness_desc_label.grid(row=3, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 4))

        # Event handlers to control dropdown switching readouts
        self.tone_combo.bind("<<ComboboxSelected>>", self.update_live_descriptions)
        self.wordiness_combo.bind("<<ComboboxSelected>>", self.update_live_descriptions)

        # Trigger original data layout compile to populate labels on boot up
        self._refresh_briefing_text_layout()

    def _on_iteration_name_changed(self, *args):
        """Live variable observer: Re-assembles the welcome readout layout text instantly on every key entry frame."""
        self._refresh_briefing_text_layout()

    def _refresh_briefing_text_layout(self):
        """Compiles configuration instructions and updates strings dynamically matching the input field."""
        # Grab current value from our string tracker or fall back to an underscore placeholder if blank
        current_name = self.controller.ui_vars["player_name"].get().strip()
        if not current_name:
            current_name = "..."

        welcome_text = (
            f"Greetings {current_name}!\n\n"
            "Welcome to your Dynamic Suit Voice diagnostic dashboard.\n\n"
            "This management utility directly bridges your customized preferences with the local "
            "voice synthesis pipeline. Adjusting settings on these tabs allows you to tailor your suit's "
            "personality and acoustic metrics cleanly before (or during) deployment.\n\n"
            "QUICK-START FLIGHT MANUAL:\n"
            "• User Profile: Assign your personalized iteration designation and choose your AI's narrative behaviors.\n"
            "• Audio Modifiers: Fine-tune post-processing filters or test customized presets inside the live sandbox.\n"
            "• Voice Model: Swap out baseline voice models or safely manage local hard drive storage footprints.\n"
            "• System Environment: Configure game directory pathways or adjust background polling refresh scales.\n\n"
            "Choose 'Cancel' to close without saving any further changes.\n"
            "Choose 'Save & Close' to save choices to disk and exit the Manager.\n"
            "Choose 'Apply Changes' at any time to save choices to disk while keeping your testing sandbox open."
        )
        self.welcome_label.config(text=welcome_text)
        self.update_live_descriptions()

    def update_live_descriptions(self, event=None):
        chosen_tone = self.controller.ui_vars["tone"].get()
        chosen_wordiness = self.controller.ui_vars["wordiness"].get()

        try:
            prompt_file = self.controller.project_root / "data" / "prompt_data.json"
            if prompt_file.exists():
                with open(prompt_file, "r", encoding="utf-8") as f:
                    pdata = json.load(f)

                tone_info = pdata.get("tones", {}).get(chosen_tone, {})
                word_info = pdata.get("wordiness", {}).get(chosen_wordiness, {})

                t_desc = tone_info.get("description", "") if isinstance(tone_info, dict) else ""
                w_desc = word_info.get("description", "") if isinstance(word_info, dict) else ""

                self.tone_desc_label.config(text=f"↳ Profile: {t_desc}")
                self.wordiness_desc_label.config(text=f"↳ Profile: {w_desc}")
        except Exception:
            pass
