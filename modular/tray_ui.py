from pathlib import Path
from PIL import Image
from pystray import Icon, Menu, MenuItem
import os
from ollama import Client


def create_tray_icon(on_quit_callback, icon_path=None):
    """Create a pystray icon using existing logic, with optional icon_path."""

    client = Client()  # <-- pass server here

    # Create menu
    tray_menu = Menu(MenuItem('Quit', on_quit_callback))

    # Load icon image
    try:
        if icon_path:
            icon_image = Path(icon_path)
        else:
            icon_image = Path(os.getenv("icon_image"))
        if icon_image.exists():
            img = Image.open(icon_image)
        else:
            raise FileNotFoundError(f"Icon not found at {icon_image}")
    except Exception as e:
        print(f"Warning: Could not load icon: {e}. Falling back to blank icon.")
        img = Image.new('RGB', (64, 64), color='black')

    # Query models from the Ollama client
    try:
        models = client.ps()
        models_list = models.models
        model_names = [m.model for m in models_list]
    except Exception as e:
        print(f"Warning: Could not query models from Ollama: {e}")
        model_names = []

    # Compose tooltip
    tooltip_lines = ["NMS DynamicSuitVoice"]
    warning_lines = []

    if len(model_names) == 1:
        prefix = "Loaded: "
        suffix = ""
    else:
        prefix = "Loaded: "
        suffix = f" +{len(model_names) - 1} more"
        warning_lines = [
            "Warning: Multiple ollama models loaded",
            "Game performance may be compromised"
        ]

    reserved = len("\n".join(tooltip_lines + warning_lines)) + len(prefix) + len(suffix) + 1
    max_model_len = 128 - reserved
    model_name = model_names[0] if model_names else "N/A"
    if len(model_name) > max_model_len:
        model_name = model_name[:max_model_len - 3] + "..."
    tooltip_lines.append(f"{prefix}{model_name}{suffix}")
    tooltip_lines += warning_lines

    tooltip_text = "\n".join(tooltip_lines)

    return Icon("NMS_DynamicSuitVoice", img, tooltip_text, tray_menu)

