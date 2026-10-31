# run_dsv.py
import sys
import socket

# ====================================================
# IMMEDIATE SINGLE-INSTANCE GUARD
# ====================================================
try:
    _instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _instance_lock.bind(("127.0.0.1", 49152))
except socket.error:
    sys.exit(0)

# ====================================================
# LIGHTWEIGHT TRAY UI RUNNER (No Large Imports Allowed Yet)
# ====================================================
import threading
from pathlib import Path
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

class FastBootTray:
    def __init__(self):
        self.running = True

        # Hardcoded fallback pathing just for the instant icon creation
        self.root_dir = Path(__file__).parent
        # Single image source target
        self.ready_icon_path = self.root_dir / "assets" / "nms_dsv.png"

        try:
            if self.ready_icon_path.exists():
                base_img = Image.open(self.ready_icon_path).convert("RGBA")
            else:
                raise FileNotFoundError()
        except Exception:
            base_img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))

        # Paint the dynamic startup background beneath the transparent icon
        w, h = base_img.size
        bg = Image.new("RGBA", (w, h), color=(220, 20, 60, 255)) # Solid colour block

        # Merge the transparent art cleanly on top of the shape
        init_img = Image.alpha_composite(bg, base_img).convert("RGB")

        self.icon = Icon(
            "NMS_DynamicSuitVoice",
            init_img,
            title="Dynamic Suit Voice - Starting Core Pipeline...",
            menu=Menu(MenuItem('Quit', self.on_quit))
        )
    def on_quit(self, _icon, _item):
        self.running = False
        self.icon.stop()

    def boot_pipeline_thread(self):
        """Runs inside a background worker thread where heavy 20-second imports are safe."""
        print("Launcher: Fast boot active. Invoking heavy engine components...")

        # LAZY-IMPORT HERE. This keeps the initial startup completely free of delay.
        from modular.config import SuitVoiceConfig
        from nms_dynamic_suit_voice_pipeline import watch_wems

        # Instantiate the configuration class now that the tray is already visible
        config = SuitVoiceConfig(init_llm=False)

        # Hand off execution control smoothly to the existing core loop
        watch_wems(self, config)

    def run(self):
        # Spin up the background compiler/initialization thread
        threading.Thread(target=self.boot_pipeline_thread, daemon=True).start()
        # Open the system tray icon instantly (0-second delay)
        self.icon.run()

if __name__ == "__main__":
    app = FastBootTray()
    app.run()
