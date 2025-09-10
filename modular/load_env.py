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
        self.suit_voice_prompt_path = Path(os.getenv("SUIT_VOICE_PROMPT_PATH"))
        with open(self.suit_voice_prompt_path, encoding="utf-8") as f:
            self.suit_voice_prompt = f.read()

        promptbuilder_path = Path(os.getenv("PROMPTBUILDER_PATH"))
        with open(promptbuilder_path, encoding="utf-8") as f:
            self.promptbuilder = json.load(f)

        # Banlist
        self.tokenized_banlist_path = Path(os.getenv("TOKENIZED_BANLIST_PATH"))
        with open(self.tokenized_banlist_path, encoding="utf-8") as f:
            self.logit_banlist = json.load(f)

        # LLM
        self.llm_model = str(Path(os.getenv("LLM_MODEL")))
        self.llm = Llama(
            model_path=self.llm_model,
            n_ctx=4096,
            n_threads=4,   # adjust as needed
            verbose=False
        )

    def __repr__(self):
        return (
            f"<SuitVoiceConfig("
            f"CHECK_INTERVAL={self.check_interval}, "
            f"MOD_DIR={self.mod_dir}, "
            f"CSV_PATH={self.csv_path}, "
            f"TEMP_WEM_DIR={self.temp_wem_dir}, "
            f"CMD_SCRIPT_PATH={self.cmd_script_path}, "
            f"TTS_MODEL={self.tts_model.model_name}, "
            f"FFMPEG={self.ffmpeg_path}, "
            f"ICON_IMAGE={self.icon_image}, "
            f"LOGGING={self.logging}, "
            f"GAME_OUTPUT_CSV={self.game_output_csv}, "
            f"SUIT_VOICE_PROMPT_PATH={self.suit_voice_prompt_path}, "
            f"TOKENIZED_BANLIST_PATH={self.tokenized_banlist_path}, "
            f"LLM_MODEL={self.llm_model}"
            f")>"
        )
