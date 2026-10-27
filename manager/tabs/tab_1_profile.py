# manager/tab_profile.py
import tkinter as tk
from tkinter import ttk
import json

class ProfileTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        """Tab 1: Selections for player identity and personality tones with dynamic explanations."""
        container = ttk.LabelFrame(self, text=" Pilot Customizations ", padding=15)
        container.pack(fill="x", padx=10, pady=10)

        phrase_settings = self.controller.user_data.get("phrase_settings", {})

        # 1. Player Callsign Input
        player_name_var = tk.StringVar(value=self.controller.user_data.get("player_name", "Interloper"))
        self.controller.ui_vars["player_name"] = player_name_var

        ttk.Label(container, text="Player / Callsign Designation:").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(container, textvariable=player_name_var, width=30).grid(row=0, column=1, sticky="w", padx=10, pady=8)

        # 2. Tone Selection
        tone_var = tk.StringVar(value=phrase_settings.get("tone", "Standard"))
        self.controller.ui_vars["tone"] = tone_var

        ttk.Label(container, text="Vocal Delivery Tone Profile:").grid(row=1, column=0, sticky="w", pady=8)
        self.tone_combo = ttk.Combobox(container, textvariable=tone_var, values=self.controller.available_tones, state="readonly", width=27)
        self.tone_combo.grid(row=1, column=1, sticky="w", padx=10, pady=8)

        self.tone_desc_label = ttk.Label(container, text="", font=("TkDefaultFont", 9, "italic"), wraplength=450, justify="left")
        self.tone_desc_label.grid(row=2, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        # 3. Wordiness Selection
        wordiness_var = tk.StringVar(value=phrase_settings.get("wordiness", "Standard"))
        self.controller.ui_vars["wordiness"] = wordiness_var

        ttk.Label(container, text="Vocal Prompt Verbiage Style:").grid(row=3, column=0, sticky="w", pady=8)
        self.wordiness_combo = ttk.Combobox(container, textvariable=wordiness_var, values=self.controller.available_wordiness, state="readonly", width=27)
        self.wordiness_combo.grid(row=3, column=1, sticky="w", padx=10, pady=8)

        self.wordiness_desc_label = ttk.Label(container, text="", font=("TkDefaultFont", 9, "italic"), wraplength=450, justify="left")
        self.wordiness_desc_label.grid(row=4, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        self.tone_combo.bind("<<ComboboxSelected>>", self.update_live_descriptions)
        self.wordiness_combo.bind("<<ComboboxSelected>>", self.update_live_descriptions)

        # ====================================================
        # NEW LANDING PAGE BRIEFING WELCOME CONTAINER
        # ====================================================
        briefing_container = ttk.LabelFrame(self, text=" Exosuit Core System Briefing ", padding=15)
        briefing_container.pack(fill="both", expand=True, padx=10, pady=10)

        welcome_text = (
            "Greetings Traveller!\n\n"
            "Welcome to your Dynamic Suit Voice diagnostic dashboard.\n\n"
            "This management utility directly bridges your customized preferences with the local "
            "vocal synthesis pipeline. Adjusting settings on these tabs allows you to tailor your suit's "
            "personality and acoustic metrics cleanly before (or during) deployment.\n\n"
            "QUICK-START FLIGHT MANUAL:\n"
            "• User Profile: Assign your custom identity designation and choose your AI's narrative behaviors.\n"
            "• Audio Modifiers: Fine-tune post-processing filters or test customized presets inside the live sandbox.\n"
            "• Voice Model: Swap out baseline voice models or safely manage local hard drive storage footprints.\n"
            "• System Environment: Configure game directory pathways or adjust background polling refresh scales.\n\n"
            "Click 'Apply Changes' at any time to save choices to disk while keeping your testing sandbox open."
        )

        briefing_label = ttk.Label(briefing_container, text=welcome_text, font=("TkDefaultFont", 10), wraplength=780, justify="left")
        briefing_label.pack(fill="both", expand=True, padx=5, pady=5)

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
