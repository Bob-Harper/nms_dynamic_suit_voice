# interface/panels/panel_1_profile.py
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox
)
from pipeline.localization import t, LOCALIZATION_DIR, get_language, set_language


LOCALE_DISPLAY_NAMES = {
    "en_us": "English (US)",
    "en_gb": "English (UK)",
    "fr_fr": "Français (FR)",
    "de_de": "Deutsch (DE)",
    "es_es": "Español (ES)",
    "es_mx": "Español (MX)",
    "pt_br": "Português (BR)",
    "ru_ru": "Русский (RU)",
    "ja_jp": "日本語 (JP)",
    "ko_kr": "한국어 (KR)",
    "zh_cn": "简体中文 (CN)",
    "zh_tw": "繁體中文 (TW)",
    "tlh_kl": "tlhIngan Hol (KL)"
}


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

        card_style = (
            "background-color: #141923; "
            "border: 1px solid #1f2430; "
            "border-radius: 6px;"
        )
        header_style = (
            "color: #ffaa00; "
            "font-weight: bold; "
            "font-family: 'Consolas', monospace; "
            "border: none;"
        )
        sublabel_style = (
            "color: #5c6773; "
            "font-size: 11px; "
            "border: none;"
        )
        combo_style = (
            "background-color: #0c0c0e; "
            "border: 1px solid #1f2430; "
            "border-radius: 4px; "
            "padding: 6px; "
            "color: #ffffff;"
        )

        # --- TOP ROW: 2-Column Split (Identity Left | UI Language Right) ---
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(15)

        # Left Card: Iteration Identity Designation
        identity_group = QWidget()
        identity_group.setStyleSheet(card_style)
        id_layout = QVBoxLayout(identity_group)
        id_layout.setContentsMargins(15, 15, 15, 15)

        id_header = QLabel(t("UI_PANEL_PROFILE_001"))
        id_header.setStyleSheet(header_style)

        id_label = QLabel(t("UI_PANEL_PROFILE_002"))
        id_label.setStyleSheet(sublabel_style)

        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText(t("UI_PANEL_PROFILE_003"))
        self.name_entry.setStyleSheet(
            "QLineEdit {"
            " background-color: #0c0c0e;"
            " border: 1px solid #1f2430;"
            " border-radius: 4px;"
            " padding: 6px;"
            " color: #ffffff;"
            " font-family: 'Consolas', monospace;"
            "}"
            "QLineEdit:focus { border: 1px solid #ffaa00; }"
        )
        self.name_entry.textChanged.connect(self._on_iteration_name_changed)

        id_layout.addWidget(id_header)
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.name_entry)
        id_layout.addStretch()

        # Right Card: Control Deck Interface Language
        ui_locale_group = QWidget()
        ui_locale_group.setStyleSheet(card_style)
        ui_locale_layout = QVBoxLayout(ui_locale_group)
        ui_locale_layout.setContentsMargins(15, 15, 15, 15)

        ui_locale_header = QLabel(t("UI_PANEL_PROFILE_004"))
        ui_locale_header.setStyleSheet(header_style)

        ui_locale_label = QLabel(t("UI_PANEL_PROFILE_005"))
        ui_locale_label.setStyleSheet(sublabel_style)

        self.ui_locale_combo = QComboBox()
        self.ui_locale_combo.setStyleSheet(combo_style)
        self._populate_ui_locales()

        ui_locale_note = QLabel(t("UI_PANEL_PROFILE_006"))
        ui_locale_note.setStyleSheet(
            "color: #5c6773; font-size: 10px; font-style: italic; border: none;"
        )

        ui_locale_layout.addWidget(ui_locale_header)
        ui_locale_layout.addWidget(ui_locale_label)
        ui_locale_layout.addWidget(self.ui_locale_combo)
        ui_locale_layout.addWidget(ui_locale_note)
        ui_locale_layout.addStretch()

        top_row_layout.addWidget(identity_group, stretch=1)
        top_row_layout.addWidget(ui_locale_group, stretch=1)
        layout.addLayout(top_row_layout)

        # --- MIDDLE CARD: Exosuit Core System Briefing ---
        briefing_group = QWidget()
        briefing_group.setStyleSheet(card_style)
        brief_layout = QVBoxLayout(briefing_group)
        brief_layout.setContentsMargins(15, 15, 15, 15)

        brief_header = QLabel(t("UI_PANEL_PROFILE_007"))
        brief_header.setStyleSheet(header_style)

        self.welcome_label = QLabel()
        self.welcome_label.setWordWrap(True)
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.welcome_label.setStyleSheet(
            "color: #ffffff; font-size: 13px; font-family: 'Segoe UI', sans-serif; border: none;"
        )

        brief_layout.addWidget(brief_header)
        brief_layout.addWidget(self.welcome_label)
        layout.addWidget(briefing_group, stretch=1)

        # --- BOTTOM CARD: 2-Column Companion Preferences ---
        prefs_group = QWidget()
        prefs_group.setStyleSheet(card_style)
        prefs_layout = QVBoxLayout(prefs_group)
        prefs_layout.setContentsMargins(15, 15, 15, 15)

        prefs_header = QLabel(t("UI_PANEL_PROFILE_008"))
        prefs_header.setStyleSheet(header_style)
        prefs_layout.addWidget(prefs_header)

        columns_frame = QWidget()
        columns_frame.setStyleSheet("border: none; background: transparent;")
        columns_layout = QHBoxLayout(columns_frame)
        columns_layout.setContentsMargins(0, 5, 0, 0)
        columns_layout.setSpacing(24)

        # Left Column: Tone & Verbiage Style
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        tone_row = QHBoxLayout()
        tone_title_label = QLabel(t("UI_PANEL_PROFILE_009"))
        tone_title_label.setMinimumWidth(165)
        self.tone_combo = QComboBox()

        if self.config and hasattr(self.config, "ui_promptdata"):
            self.tone_combo.addItems(list(self.config.ui_promptdata.get("tones", {}).keys()))

        self.tone_combo.setMinimumWidth(190)
        self.tone_combo.setStyleSheet(combo_style)
        self.tone_combo.currentTextChanged.connect(self._update_live_descriptions)
        tone_row.addWidget(tone_title_label)
        tone_row.addWidget(self.tone_combo)
        tone_row.addStretch()
        left_col.addLayout(tone_row)

        self.tone_desc_label = QLabel()
        self.tone_desc_label.setWordWrap(True)
        self.tone_desc_label.setStyleSheet(
            "color: #5c6773; font-size: 11px; font-style: italic; border: none; padding-left: 170px;"
        )
        left_col.addWidget(self.tone_desc_label)

        word_row = QHBoxLayout()
        word_title_label = QLabel(t("UI_PANEL_PROFILE_010"))
        word_title_label.setMinimumWidth(165)
        self.wordiness_combo = QComboBox()

        if self.config and hasattr(self.config, "ui_promptdata"):
            self.wordiness_combo.addItems(list(self.config.ui_promptdata.get("wordiness", {}).keys()))

        self.wordiness_combo.setMinimumWidth(190)
        self.wordiness_combo.setStyleSheet(combo_style)
        self.wordiness_combo.currentTextChanged.connect(self._update_live_descriptions)
        word_row.addWidget(word_title_label)
        word_row.addWidget(self.wordiness_combo)
        word_row.addStretch()
        left_col.addLayout(word_row)

        self.wordiness_desc_label = QLabel()
        self.wordiness_desc_label.setWordWrap(True)
        self.wordiness_desc_label.setStyleSheet(
            "color: #5c6773; font-size: 11px; font-style: italic; border: none; padding-left: 170px;"
        )
        left_col.addWidget(self.wordiness_desc_label)
        left_col.addStretch()

        # Right Column: Exosuit Voice Language (Groundwork / Coming Soon)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        voice_lang_row = QHBoxLayout()
        voice_lang_label = QLabel(t("UI_PANEL_PROFILE_011"))
        voice_lang_label.setMinimumWidth(155)

        self.voice_locale_combo = QComboBox()
        self.voice_locale_combo.setMinimumWidth(190)
        self.voice_locale_combo.setStyleSheet(
            "background-color: #0c0c0e; "
            "border: 1px solid #1f2430; "
            "border-radius: 4px; "
            "padding: 6px; "
            "color: #66666d;"
        )
        self.voice_locale_combo.addItem(t("UI_PANEL_PROFILE_012"), "en_us")
        self.voice_locale_combo.setEnabled(False)

        voice_lang_row.addWidget(voice_lang_label)
        voice_lang_row.addWidget(self.voice_locale_combo)
        voice_lang_row.addStretch()
        right_col.addLayout(voice_lang_row)

        voice_lang_desc = QLabel(t("UI_PANEL_PROFILE_013"))
        voice_lang_desc.setWordWrap(True)
        voice_lang_desc.setStyleSheet(
            "color: #5c6773; font-size: 11px; font-style: italic; border: none; padding-left: 160px;"
        )
        right_col.addWidget(voice_lang_desc)
        right_col.addStretch()

        columns_layout.addLayout(left_col, stretch=3)
        columns_layout.addLayout(right_col, stretch=2)
        prefs_layout.addWidget(columns_frame)
        layout.addWidget(prefs_group)

    def _populate_ui_locales(self):
        """Scans data/localization/ for installed locale folders and populates the dropdown."""
        self.ui_locale_combo.clear()
        discovered = []
        if LOCALIZATION_DIR.is_dir():
            for entry in sorted(LOCALIZATION_DIR.iterdir()):
                if entry.is_dir() and any(entry.glob("*.json")):
                    discovered.append(entry.name.lower())

        if not discovered:
            discovered = ["en_us"]

        for code in discovered:
            friendly = LOCALE_DISPLAY_NAMES.get(code, code)
            label = f"{friendly} [{code}]" if friendly != code else code
            self.ui_locale_combo.addItem(label, code)

    def _initialize_data_fields(self):
        """Loads configuration fields from the configuration instance."""
        if not self.config:
            return

        user_data = self.config.user_customization

        self.name_entry.setText(self.config.player_name)
        self.tone_combo.setCurrentText(self.config.current_tone)
        self.wordiness_combo.setCurrentText(self.config.current_wordiness)

        active_ui_locale = str(user_data.get("ui_locale") or get_language() or "en_us").lower()
        idx = self.ui_locale_combo.findData(active_ui_locale)
        if idx != -1:
            self.ui_locale_combo.setCurrentIndex(idx)

        self._refresh_briefing_text_layout()

    def _on_iteration_name_changed(self, text):
        self._refresh_briefing_text_layout()

    def _refresh_briefing_text_layout(self):
        current_name = self.name_entry.text().strip()
        if not current_name:
            current_name = "..."

        welcome_text = t(
            "UI_PANEL_PROFILE_014",
            name=current_name,
            engage_btn=t("UI_DECK_INIT_009"),
        )
        self.welcome_label.setText(welcome_text)
        self._update_live_descriptions()

    def _update_live_descriptions(self, event_text=None):
        if not self.config or not hasattr(self.config, "ui_promptdata"):
            return

        chosen_tone = self.tone_combo.currentText()
        chosen_wordiness = self.wordiness_combo.currentText()

        t_desc = self.config.ui_promptdata.get("tones", {}).get(chosen_tone, {}).get("description")
        w_desc = self.config.ui_promptdata.get("wordiness", {}).get(chosen_wordiness, {}).get("description")

        self.tone_desc_label.setText(
            t("UI_PANEL_PROFILE_015", desc=t_desc) if t_desc else t("UI_PANEL_PROFILE_016")
        )
        self.wordiness_desc_label.setText(
            t("UI_PANEL_PROFILE_017", desc=w_desc) if w_desc else t("UI_PANEL_PROFILE_018")
        )

    def gather_settings(self):
        if not self.config:
            return

        self.config.user_customization["player_name"] = self.name_entry.text().strip()

        selected_ui_locale = self.ui_locale_combo.currentData() or "en_us"
        self.config.user_customization["ui_locale"] = selected_ui_locale
        set_language(selected_ui_locale)

        if "voice_locale" not in self.config.user_customization:
            self.config.user_customization["voice_locale"] = (
                self.voice_locale_combo.currentData() or "en_us"
            )

        if "phrase_settings" not in self.config.user_customization:
            self.config.user_customization["phrase_settings"] = {}

        self.config.user_customization["phrase_settings"]["tone"] = self.tone_combo.currentText()
        self.config.user_customization["phrase_settings"]["wordiness"] = self.wordiness_combo.currentText()
