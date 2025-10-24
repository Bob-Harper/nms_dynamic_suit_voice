# config.py
import os
import csv
import sys
import json
import shutil
from pathlib import Path
from llama_cpp import Llama
from dotenv import load_dotenv
from TTS.api import TTS  # coqui-tts fork


def resolve_path(env_var: str, root: Path, must_exist=True) -> Path:
    """Resolve env var into an absolute Path relative to project root if needed."""
    val = os.getenv(env_var)
    if not val:
        raise ValueError(f"{env_var} not set in environment")
    p = Path(val.strip('"'))
    if not p.is_absolute():
        p = root / p
    if must_exist and not p.exists():
        raise FileNotFoundError(f"{env_var} points to missing file: {p}")
    return p


class SuitVoiceConfig:
    def __init__(self, env_file: str = "suit_voice.env", init_llm: bool = True):
        # anchor to project root (parent of modular/)
        root_dir = Path(__file__).parent.parent
        load_dotenv(dotenv_path=root_dir / env_file)

        self.check_interval = float(os.getenv("CHECK_INTERVAL"))
        self.mod_dir = resolve_path("MOD_DIR", root_dir, must_exist=False)
        self.csv_path = resolve_path("CSV_PATH", root_dir)
        self.intent_map = self.load_intent_map(self.csv_path)
        self.temp_wem_dir = resolve_path("TEMP_WEM_DIR", root_dir, must_exist=False)
        self.temp_wem_dir.mkdir(parents=True, exist_ok=True)
        self.temp_wav_dir = resolve_path("TEMP_WAV_DIR", root_dir, must_exist=False)
        self.temp_wav_dir.mkdir(parents=True, exist_ok=True)

        self.cmd_script_path = resolve_path("CMD_SCRIPT_PATH", root_dir, must_exist=False)

        # TTS model
        tts_model_name = os.getenv("TTS_MODEL")
        if not tts_model_name:
            raise ValueError("TTS_MODEL not set in environment")
        self.tts_model_name = tts_model_name
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

        self.icon_image = resolve_path("ICON_IMAGE", root_dir, must_exist=False)
        self.logging = os.getenv("LOGGING", "false").strip().lower() == "true"
        self.game_output_csv = resolve_path("GAME_OUTPUT_CSV", root_dir, must_exist=False)
        self.create_no_window = 0x08000000 if sys.platform == "win32" else 0

        # Suit voice prompt files
        self.suit_voice_base_path = resolve_path("SUIT_VOICE_BASE_PATH", root_dir)
        self.suit_voice_base = self.suit_voice_base_path.read_text(encoding="utf-8")

        self.suit_voice_dynamic_path = resolve_path("SUIT_VOICE_DYNAMIC_PATH", root_dir)
        self.suit_voice_dynamic = self.suit_voice_dynamic_path.read_text(encoding="utf-8")

        self.suit_voice_combat_path = resolve_path("SUIT_VOICE_COMBAT_PATH", root_dir)
        self.suit_voice_combat = self.suit_voice_combat_path.read_text(encoding="utf-8")
        self.milcat_enable_reasoning = os.getenv("COMBAT_CATEGORIES_ALLOW_REASONING")

        self.promptdata_path = resolve_path("PROMPTdata_PATH", root_dir)
        self.promptdata = json.loads(self.promptdata_path.read_text(encoding="utf-8"))

        # Banlist
        self.tokenized_logits_path = resolve_path("TOKENIZED_LOGITS_PATH", root_dir)
        self.logit_banlist = json.loads(self.tokenized_logits_path.read_text(encoding="utf-8"))

        # LLM model
        self.llm_model = str(resolve_path("LLM_MODEL", root_dir))
        self.llm = None
        if init_llm:
            self.llm = Llama(
                model_path=self.llm_model,
                n_ctx=40960,
                n_batch=1024,
                n_threads=4,
                verbose=False
            )

        # Runtime state
        self.current_tone = os.getenv("PHRASE_TONE")
        self.current_wordiness = os.getenv("PHRASE_WORDINESS")
        self.player_name = os.getenv("PLAYER_NAME")
        self.units_received = os.getenv("UNITS_CATEGORY_RECEIVED")
        self.units_insufficient = os.getenv("UNITS_CATEGORY_INSUFFICIENT")
        # Categories that override prompting rules
        mil_cat_str = os.getenv("MIL_CATEGORIES", "")
        self.mil_cat = [x.strip() for x in mil_cat_str.split(",") if x.strip()]
        # Max recent lines per session from .env
        self.max_session_lines = int(os.getenv("MAX_SESSION_LINES", 25))

        # Recent lines store: dict keyed by WEM ID
        self.recent_lines_text = {}  # {wem_id_str: [line1, line2, ...]}
         # parse comma-separated quick response IDs as string NOT integer
        quick_response_str = os.getenv("QUICK_RESPONSE_IDS", "")
        self.quick_response_ids = [x.strip() for x in quick_response_str.split(",") if x.strip()]

    def get_tone(self) -> str:
        return self.current_tone

    def get_wordiness(self, category: str) -> str:
        if category in self.mil_cat:
            return "Observer"
        return self.current_wordiness

    @staticmethod
    def load_intent_map(csv_path: Path) -> dict:
        i_intent_map = {}
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    wem_number = (row.get('WEM_number') or '').strip()
                    original_phrase = (row.get('Transcription') or '').strip()
                    category = (row.get('Category') or '').strip()
                    intent = (row.get('Intent') or '').strip()
                    i_intent_map[wem_number] = {
                        "Transcription": original_phrase,
                        "Category": category,
                        "Intent": intent,
                    }
        except Exception as e1:
            print(f"Error loading intent map: {e1}")
        return i_intent_map
