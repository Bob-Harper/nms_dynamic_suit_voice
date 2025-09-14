# tray_ui.py
import os
import threading
from pathlib import Path
from PIL import Image
from pystray import Icon, Menu, MenuItem


class TrayUI:
    def __init__(self, config, watch_target):
        self.config = config
        self.intent_map = config.intent_map
        self.watch_target = watch_target
        self.running = True

        # Load icon
        try:
            icon_path = Path(os.getenv("ICON_IMAGE"))
            if icon_path.exists():
                img = Image.open(icon_path)
            else:
                raise FileNotFoundError(f"Icon not found at {icon_path}")
        except Exception as e:
            print(f"Warning: Could not load icon: {e}. Falling back to blank icon.")
            img = Image.new('RGB', (64, 64), color='black')

        self.icon = Icon(
            "NMS_DynamicSuitVoice",
            img,
            self._make_tooltip(),
            self._make_menu()
        )

    # === Menu builders ===
    def _make_menu(self):

        return Menu(
            MenuItem('Quit', self.on_quit)
        )

    def _make_tooltip(self):
        return f"No Man's Sky Dynamic Suit Voice"

    # === Actions ===
    def on_quit(self, _icon, _item):
        self.running = False
        self.icon.stop()

    # === Runner ===
    def run(self):
        watcher = threading.Thread(target=self.watch_target, args=(self,), daemon=True)
        watcher.start()
        self.icon.run()

    # === Set aside for future implementation ===
    def set_tone(self, selected):
        self.config.current_tone = selected
        self._refresh()

    def set_wordiness(self, selected):
        self.config.current_wordiness = selected
        self._refresh()

    def _refresh(self):
        self.icon.title = self._make_tooltip()
        self.icon.update_menu()

    def _make_tooltip_with_options(self):
        return f"No Man's Sky Dynamic Voice\nStyle: {self.config.current_wordiness}\nTone: {self.config.current_tone}"

    def _make_menu_with_options(self):
        tone_menu = Menu(
            *(MenuItem(
                tone,
                lambda _, t=tone: self.set_tone(t),
                checked=lambda item, t=tone: self.config.current_tone == t
            ) for tone in self.config.promptbuilder["tones"].keys())
        )
        wordiness_menu = Menu(
            *(MenuItem(
                level,
                lambda _, w=level: self.set_wordiness(w),
                checked=lambda item, w=level: self.config.current_wordiness == w
            ) for level in self.config.promptbuilder["wordiness"].keys() if level != "Observer")
        )

        return Menu(
            MenuItem('Tone', tone_menu),
            MenuItem('Wordiness', wordiness_menu),
            MenuItem('Quit', self.on_quit)
        )
