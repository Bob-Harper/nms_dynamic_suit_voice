# tray_ui.py
import os
import threading
from pathlib import Path
from PIL import Image
from pystray import Icon, Menu, MenuItem
# from debug.log_config import debug_print  # this page works fine


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

    @staticmethod
    def _make_tooltip():
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
