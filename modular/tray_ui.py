# tray_ui.py
import os
import threading
from pathlib import Path
from PIL import Image
from pystray import Icon, Menu, MenuItem
from extras.cache_topup_to_max import fill_cache_for_ids
from modular.config import SuitVoiceConfig
from debug.logging_utils import debug_print

class TrayUI:
    def __init__(self, config: SuitVoiceConfig, watch_target):
        self.config = config
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
            MenuItem('Manage Cache', self._manage_cache_menu),
            MenuItem('Quit', self.on_quit)
        )

    def _manage_cache_menu(self, icon, item):
        # Submenu items
        self.icon.menu = Menu(
            MenuItem('Top Up Cache', self._top_up_cache),
            MenuItem('Show Cache Status', self._show_cache_status),
            MenuItem('Back', self._restore_main_menu)
        )
        self.icon.update_menu()

    def _restore_main_menu(self, icon=None, item=None):
        self.icon.menu = self._make_menu()
        self.icon.update_menu()

    # === Actions ===
    def on_quit(self, _icon, _item):
        self.running = False
        self.icon.stop()

    def _top_up_cache(self, icon, item):
        threading.Thread(target=self._top_up_thread, daemon=True).start()

    def _top_up_thread(self):
        debug_print("TrayUI: Starting cache top-up")
        # Fill cache for all IDs marked as Used="Yes"
        import csv
        csv_path = self.config.csv_path
        wem_ids_to_topup = []

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Used", "").strip().lower() == "yes":
                    wem_ids_to_topup.append(row["WEM_number"])

        fill_cache_for_ids(wem_ids_to_topup, max_count=self.config.quick_cache_max)
        debug_print("TrayUI: Cache top-up complete")

    def _show_cache_status(self, icon, item):
        threading.Thread(target=self._show_cache_thread, daemon=True).start()

    def _show_cache_thread(self):
        total_files = 0
        for wem_dir in self.config.quick_cache_dir.iterdir():
            if wem_dir.is_dir():
                total_files += len(list(wem_dir.glob("*.wem")))
        debug_print(f"TrayUI: Total cached WEM files: {total_files}")

    # === Tooltip ===
    @staticmethod
    def _make_tooltip():
        return "No Man's Sky Dynamic Suit Voice"

    # === Runner ===
    def run(self):
        watcher = threading.Thread(target=self.watch_target, args=(self,), daemon=True)
        watcher.start()
        self.icon.run()
