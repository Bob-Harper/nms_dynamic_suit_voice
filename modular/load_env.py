# load_env.py
import os
import sys
import json
import shutil
from pathlib import Path
from llama_cpp import Llama
from dotenv import load_dotenv
from TTS.api import TTS  # coqui-tts fork

class SuitVoiceConfig:
    def __init__(self, env_file: str = "suit_voice.env"):
        load_dotenv(dotenv_path=Path(__file__).parent.parent / env_file)

        self.check_interval = float(os.getenv("CHECK_INTERVAL"))
        self.mod_dir = Path(os.getenv("MOD_DIR").strip('"'))
        self.csv_path = Path(os.getenv("CSV_PATH"))

        self.temp_wem_dir = Path(os.getenv("TEMP_WEM_DIR").strip('"'))
        self.temp_wem_dir.mkdir(parents=True, exist_ok=True)

        self.cmd_script_path = Path(os.getenv("CMD_SCRIPT_PATH").strip('"'))

        # TTS model
        tts_model_name = os.getenv("TTS_MODEL")
        if not tts_model_name:
            raise ValueError("TTS_MODEL not set in environment")
        self.tts_model = TTS(model_name=tts_model_name)

        # FFMPEG
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            ffmpeg_env = os.getenv("FFMPEG_PATH")
            if ffmpeg_env:
                ffmpeg_path = Path(ffmpeg_env.strip('"'))
                os.environ["PATH"] = str(ffmpeg_path.parent) + ";" + os.environ.get("PATH", "")
            else:
                raise SystemExit("ffmpeg not found on PATH and FFMPEG_PATH not set in .env")

        self.ffmpeg_path = Path(ffmpeg_path)

        self.icon_image = Path(os.getenv("ICON_IMAGE"))
        self.logging = os.getenv("LOGGING", "false").strip().lower() == "true"
        self.game_output_csv = Path(os.getenv("GAME_OUTPUT_CSV"))
        self.create_no_window = 0x08000000 if sys.platform == "win32" else 0

        # Suit voice prompt
        self.suit_voice_base_path = Path(os.getenv("SUIT_VOICE_BASE_PATH"))
        with open(self.suit_voice_base_path, encoding="utf-8") as f:
            self.suit_voice_base = f.read()

        self.suit_voice_dynamic_path = Path(os.getenv("SUIT_VOICE_DYNAMIC_PATH"))
        with open(self.suit_voice_dynamic_path, encoding="utf-8") as f:
            self.suit_voice_dynamic = f.read()

        self.suit_voice_combat_path = Path(os.getenv("SUIT_VOICE_COMBAT_PATH"))
        with open(self.suit_voice_combat_path, encoding="utf-8") as f:
            self.suit_voice_combat = f.read()

        self.promptbuilder_path = Path(os.getenv("PROMPTBUILDER_PATH"))
        with open(self.promptbuilder_path, encoding="utf-8") as f:
            self.promptbuilder = json.load(f)

        # Banlist
        self.tokenized_banlist_path = Path(os.getenv("TOKENIZED_BANLIST_PATH"))
        with open(self.tokenized_banlist_path, encoding="utf-8") as f:
            self.logit_banlist = json.load(f)

        # LLM
        self.llm_model = str(Path(os.getenv("LLM_MODEL")))
        self.llm = Llama(
            model_path=self.llm_model,
            # n_ctx=4096, # does it help?
            n_ctx=32768,  # full context window
            n_batch=1024,  # helps performance
            n_threads=4,   # adjust as needed
            verbose=False
        )
