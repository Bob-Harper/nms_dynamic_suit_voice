import tkinter as tk
from tkinter import ttk, filedialog, font
from pathlib import Path
import subprocess
import sys
import time
from TTS.api import TTS
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Default settings
DEFAULT_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
XTTS_MODEL = True
DEFAULT_EMBED = None
DEFAULT_GAIN = 5
DEFAULT_ATEMPO = 1.1
DEFAULT_RATE = 0.52
DEFAULT_SR = 44100

base_dir = Path("embeds")
base_dir.mkdir(exist_ok=True)

def generate_tts(text, model_name, embed, gain_db, atempo, rate, output_path):
    asetrate = int(DEFAULT_SR * rate)
    temp_wav = base_dir / "temp.wav"

    # init model
    tts = TTS(model_name=model_name)
    # tts.to("cuda")  # for gpu
    tts.to("cpu")
    ref_dir = Path(r"C:\NMS_SUIT_VOICE\embeds\originalvoicefiles")
    speaker_wav = list(ref_dir.glob("*.wav"))  # list of Path objects

    start = time.time()
    if embed:
        tts.tts_to_file(text=text, file_path=str(temp_wav), speaker_wav=embed, language="en",)
    else:
        tts.tts_to_file(text=text, file_path=str(temp_wav), speaker_wav=speaker_wav, language="en",)
    mid = time.time()

    subprocess.run([
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(temp_wav),
        "-af", f"volume={gain_db}dB,atempo={atempo},asetrate={asetrate}",
        str(output_path)
    ], check=True, creationflags=CREATE_NO_WINDOW)
    end = time.time()

    return mid - start, end - mid, end - start

# GUI setup
root = tk.Tk()
root.title("TTS Tester")
# Example: 12pt instead of tiny defaults
default_font = font.nametofont("TkDefaultFont")
default_font.configure(size=12)
# after you configure TkDefaultFont, add a text style font
text_font = font.nametofont("TkTextFont")
text_font.configure(size=12, family="Consolas")  # or another clean font
root.configure(bg="#2b2b2b")
# convenience dict for consistent look
text_cfg = {
    "bg": "#1e1e1e",
    "fg": "#dddddd",
    "insertbackground": "#ffffff",  # caret color
    "font": text_font,
}
text_font = font.nametofont("TkTextFont")
text_font.configure(size=12)

fixed_font = font.nametofont("TkFixedFont")
fixed_font.configure(size=12)

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background="#2b2b2b")
style.configure("TLabel", background="#2b2b2b", foreground="#dddddd")
style.configure("TButton", background="#444444", foreground="#eeeeee")

pad = 10
# Text input
ttk.Label(root, text="Input Text:").pack(anchor="w")
text_box = tk.Text(root, height=6, width=60, **text_cfg)
text_box.pack()

# Model field
ttk.Label(root, text="Model Name:").pack(anchor="w")
model_entry = tk.Entry(root, width=60, bg="#1e1e1e", fg="#dddddd", insertbackground="#ffffff")
model_entry.insert(0, DEFAULT_MODEL)
model_entry.pack()

# Embed field
ttk.Label(root, text="Embed WAV (optional):").pack(anchor="w")
embed_entry = tk.Entry(root, width=60, bg="#1e1e1e", fg="#dddddd", insertbackground="#ffffff")
embed_entry.pack()

def browse_embed():
    path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if path:
        embed_entry.delete(0, tk.END)
        embed_entry.insert(0, path)

ttk.Button(root, text="Browse", command=browse_embed).pack()

# Params
param_frame = tk.Frame(root)
param_frame.pack()

ttk.Label(param_frame, text="Gain (dB)").grid(row=0, column=0)
gain_entry = tk.Entry(param_frame, width=5, bg="#1e1e1e", fg="#dddddd", insertbackground="#ffffff")
gain_entry.insert(0, str(DEFAULT_GAIN))
gain_entry.grid(row=0, column=1)

ttk.Label(param_frame, text="Tempo").grid(row=0, column=2)
atempo_entry = tk.Entry(param_frame, width=5, bg="#1e1e1e", fg="#dddddd", insertbackground="#ffffff")
atempo_entry.insert(0, str(DEFAULT_ATEMPO))
atempo_entry.grid(row=0, column=3)

ttk.Label(param_frame, text="Rate").grid(row=0, column=4)
rate_entry = tk.Entry(param_frame, width=5, bg="#1e1e1e", fg="#dddddd", insertbackground="#ffffff")
rate_entry.insert(0, str(DEFAULT_RATE))
rate_entry.grid(row=0, column=5)

# Output filename
ttk.Label(root, text="Output Filename:").pack(anchor="w")
output_entry = tk.Entry(root, width=60, bg="#1e1e1e", fg="#dddddd", insertbackground="#ffffff")
output_entry.insert(0, "xx_test_tts_output.wav")
output_entry.pack()

# --- after the input text box setup ---

# Processed text preview (read-only)
ttk.Label(root, text="Processed Text (to TTS):").pack(anchor="w")
processed_box = tk.Text(root, height=6, width=60, state="disabled", **text_cfg)
processed_box.pack()

def update_processed_preview():
    """Take input text and apply preprocessing, show result."""
    raw = text_box.get("1.0", tk.END).strip()
    # Example preprocessing: wrap in quotes, replace manual newlines
    processed = '"' + raw.replace("\n", "\\n\n") + '"'
    # Update box
    processed_box.config(state="normal")
    processed_box.delete("1.0", tk.END)
    processed_box.insert("1.0", processed)
    processed_box.config(state="disabled")
    return processed

# --- Status box at the bottom ---
ttk.Label(root, text="Status:").pack(anchor="w")
status_box = tk.Text(root, height=6, width=60, state="disabled", **text_cfg)
status_box.pack()

def update_status(message: str):
    """Append a message to the status box."""
    status_box.config(state="normal")
    status_box.insert("end", message + "\n")
    status_box.see("end")  # scroll to latest message
    status_box.config(state="disabled")

def run_tts():
    text = update_processed_preview()  # get the processed version
    model = model_entry.get().strip()
    embed = embed_entry.get().strip() or None
    gain_db = float(gain_entry.get())
    atempo = float(atempo_entry.get())
    rate = float(rate_entry.get())
    output_path = Path(output_entry.get())

    update_status("Starting TTS generation...")

    try:
        t1, t2, total = generate_tts(text, model, embed, gain_db, atempo, rate, output_path)
        update_status(f"TTS generated in {t1:.2f}s | FFmpeg processed in {t2:.2f}s | Total {total:.2f}s")
        update_status(f"Output saved to: {output_path}")
    except Exception as e:
        update_status(f"Error during TTS generation: {str(e)}")

def play_output():
    path = Path(output_entry.get())
    if not path.exists():
        update_status(f"Output file not found: {path}")
        return

    update_status(f"Playing output file: {path}")
    try:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", str(path)], creationflags=CREATE_NO_WINDOW)
        update_status("Playback finished.")
    except Exception as e:
        update_status(f"Error during playback: {str(e)}")


ttk.Button(root, text="Generate TTS", command=run_tts).pack(pady=5)
ttk.Button(root, text="Play Output", command=play_output).pack(pady=5)

root.mainloop()
