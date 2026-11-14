# interface/panels/panel_1_profile.py
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox
)

class ProfilePanel(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._build_ui()
        self._initialize_data_fields()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)

        identity_group = QWidget()
        identity_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        id_layout = QVBoxLayout(identity_group)
        id_layout.setContentsMargins(15, 15, 15, 15)

        id_header = QLabel("ITERATION IDENTITY DESIGNATION")
        id_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")

        id_label = QLabel("Designate the callsign the Suit AI shall use to address you:")
        id_label.setStyleSheet("color: #5c6773; font-size: 11px; border: none;")

        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText("e.g., Interloper, Commander, Traveler...")
        self.name_entry.setStyleSheet("""
            QLineEdit {
                background-color: #0c0c0e;
                border: 1px solid #1f2430;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus { border: 1px solid #ffaa00; }
        """)
        self.name_entry.textChanged.connect(self._on_iteration_name_changed)

        id_layout.addWidget(id_header)
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.name_entry)
        layout.addWidget(identity_group)

        briefing_group = QWidget()
        briefing_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        brief_layout = QVBoxLayout(briefing_group)
        brief_layout.setContentsMargins(15, 15, 15, 15)

        brief_header = QLabel("EXOSUIT CORE SYSTEM BRIEFING")
        brief_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")

        self.welcome_label = QLabel()
        self.welcome_label.setWordWrap(True)
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.welcome_label.setStyleSheet("color: #ffffff; font-size: 13px; font-family: 'Segoe UI', sans-serif; border: none;")

        brief_layout.addWidget(brief_header)
        brief_layout.addWidget(self.welcome_label)
        layout.addWidget(briefing_group, stretch=1)

        prefs_group = QWidget()
        prefs_group.setStyleSheet("background-color: #141923; border: 1px solid #1f2430; border-radius: 6px;")
        prefs_layout = QVBoxLayout(prefs_group)
        prefs_layout.setContentsMargins(15, 15, 15, 15)

        prefs_header = QLabel("COMPANION PREFERENCES")
        prefs_header.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        prefs_layout.addWidget(prefs_header)

        selectors_frame = QWidget()
        selectors_frame.setStyleSheet("border: none; background: transparent;")
        selectors_layout = QVBoxLayout(selectors_frame)
        selectors_layout.setContentsMargins(0, 5, 0, 0)
        selectors_layout.setSpacing(12)

        tone_row = QHBoxLayout()
        tone_title_label = QLabel("Companion AI Tone Profile:")
        tone_title_label.setMinimumWidth(180)
        self.tone_combo = QComboBox()

        # Guard: Check that the memory dictionary is mapped before accessing keys
        if self.config and hasattr(self.config, 'ui_promptdata'):
            self.tone_combo.addItems(list(self.config.ui_promptdata.get("tones", {}).keys()))

        self.tone_combo.setMinimumWidth(220)
        self.tone_combo.setStyleSheet("background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; padding: 4px; color: #ffffff;")
        self.tone_combo.currentTextChanged.connect(self._update_live_descriptions)
        tone_row.addWidget(tone_title_label)
        tone_row.addWidget(self.tone_combo)
        tone_row.addStretch()
        selectors_layout.addLayout(tone_row)

        self.tone_desc_label = QLabel()
        self.tone_desc_label.setStyleSheet("color: #5c6773; font-size: 11px; font-style: italic; border: none; padding-left: 185px;")
        selectors_layout.addWidget(self.tone_desc_label)

        word_row = QHBoxLayout()
        word_title_label = QLabel("Companion AI Verbiage Style:")
        word_title_label.setMinimumWidth(180)
        self.wordiness_combo = QComboBox()

        if self.config and hasattr(self.config, 'ui_promptdata'):
            self.wordiness_combo.addItems(list(self.config.ui_promptdata.get("wordiness", {}).keys()))

        self.wordiness_combo.setMinimumWidth(220)
        self.wordiness_combo.setStyleSheet("background-color: #0c0c0e; border: 1px solid #1f2430; border-radius: 4px; padding: 4px; color: #ffffff;")
        self.wordiness_combo.currentTextChanged.connect(self._update_live_descriptions)
        word_row.addWidget(word_title_label)
        word_row.addWidget(self.wordiness_combo)
        word_row.addStretch()
        selectors_layout.addLayout(word_row)

        self.wordiness_desc_label = QLabel()
        self.wordiness_desc_label.setStyleSheet("color: #5c6773; font-size: 11px; font-style: italic; border: none; padding-left: 185px;")
        selectors_layout.addWidget(self.wordiness_desc_label)

        prefs_layout.addWidget(selectors_frame)
        layout.addWidget(prefs_group)

    def _initialize_data_fields(self):
        """Loads configuration fields from the configuration instance."""
        if not self.config:
            return

        user_data = self.config.user_customization
        phrase_settings = user_data.get("phrase_settings", {})

        self.name_entry.setText(self.config.player_name)
        self.tone_combo.setCurrentText(self.config.current_tone)
        self.wordiness_combo.setCurrentText(self.config.current_wordiness)
        self._refresh_briefing_text_layout()

    def _on_iteration_name_changed(self, text):
        self._refresh_briefing_text_layout()

    def _refresh_briefing_text_layout(self):
        current_name = self.name_entry.text().strip()
        if not current_name:
            current_name = "..."

        welcome_text = (
            f"Greetings {current_name}!\n\n"
            "Welcome to your Exosuit Integration Control Deck.\n\n"
            "This centralized dashboard directly manages your customized preferences while serving as the primary launch vehicle "
            "for the active system surveillance loop. Running the engine directly inside this frame satisfies OS security boundaries.\n\n"
            "OPERATION MANUAL, TL;DR EDITION:\n"
            "• User Profile to update your operator designation callsign and select AI behavioral guidelines directly from data profiles.\n"
            "• Audio Modifiers to configure and tune digital signal processing matrix settings in real time.\n\n"
            f"When ready, 'ENGAGE AI CORE' using the button above. May your journey bring you interesting surprises.  Good luck, {current_name}! "
        )
        self.welcome_label.setText(welcome_text)
        self._update_live_descriptions()

    def _update_live_descriptions(self, event_text=None):
        if not self.config or not hasattr(self.config, 'ui_promptdata'):
            return

        chosen_tone = self.tone_combo.currentText()
        chosen_wordiness = self.wordiness_combo.currentText()

        t_desc = self.config.ui_promptdata.get("tones", {}).get(chosen_tone, {}).get("description")
        w_desc = self.config.ui_promptdata.get("wordiness", {}).get(chosen_wordiness, {}).get("description")

        self.tone_desc_label.setText(f"↳ Profile: {t_desc}" if t_desc else "↳ Profile: Default tone metrics active.")
        self.wordiness_desc_label.setText(f"↳ Profile: {w_desc}" if w_desc else "↳ Profile: Default narrative length active.")

    def gather_settings(self):
        if not self.config:
            return

        self.config.user_customization["player_name"] = self.name_entry.text().strip()

        if "phrase_settings" not in self.config.user_customization:
            self.config.user_customization["phrase_settings"] = {}

        self.config.user_customization["phrase_settings"]["tone"] = self.tone_combo.currentText()
        self.config.user_customization["phrase_settings"]["wordiness"] = self.wordiness_combo.currentText()