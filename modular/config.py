# config.py
import csv
import json
import os
import shutil
import sys
from pathlib import Path
from llama_cpp import Llama, Optional
from TTS.api import TTS  # coqui-tts fork

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

class SuitVoiceConfig:
    def __init__(self, init_llm: bool = True):
        # Anchor to project root (parent of modular/)
        root_dir = Path(__file__).parent.parent
        config_dir = root_dir / "config"

        # Load file structures
        self.dsv2wem = load_json(config_dir / "dsv2wem_config.json")
        self.environment = load_json(config_dir / "environment_config.json")
        self.llm_prompting = load_json(config_dir / "llm_prompting.json")
        self.default_customization = load_json(config_dir / "default_customization.json")
        self.user_customization = load_json(config_dir / "user_customization.json")

        # Merge defaults with custom user tweaks cleanly
        self.customization = deep_merge(
            self.default_customization,
            self.user_customization
        )

        # --- RUNTIME SETTINGS ---
        runtime = self.environment.get("runtime", {})
        self.check_interval = float(runtime.get("check_interval", 0.1))
        self.max_session_lines = int(runtime.get("max_session_lines", 25))
        self.quick_cache_max = int(runtime.get("quick_cache_max", 16))

        # ====================================================
        # CORE FILESYSTEM PATHS (From environment_config.json -> "paths")
        # ====================================================
        paths = self.environment.get("paths", {})

        # Game Mod Directory (Must exist to track file updates)
        self.mod_dir = self.resolve_json_path(paths.get("mod_dir"), root_dir, must_exist=True)

        # Tray App UI Icon (Force to clean string format for PIL/pystray compatibility)
        icon_path_obj = self.resolve_json_path(paths.get("icon_image"), root_dir, must_exist=True)
        self.icon_image = str(icon_path_obj)

        # Engine Cache Locations (Will be auto-provisioned safely below)
        self.temp_wem_dir = self.resolve_json_path(paths.get("temp_wem_dir"), root_dir, must_exist=False)
        self.temp_wav_dir = self.resolve_json_path(paths.get("temp_wav_dir"), root_dir, must_exist=False)
        self.quick_cache_dir = self.resolve_json_path(paths.get("quick_cache_dir"), root_dir, must_exist=False)


        # Window platform subprocess flags
        self.create_no_window = 0x08000000 if sys.platform == "win32" else 0

        # Enforce workspace directories (Safe loop: all paths are strict non-nullable Path types)
        for d in [self.temp_wem_dir, self.temp_wav_dir, self.quick_cache_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # ====================================================
        # EXTERNAL SYSTEM UTILITIES (From environment_config.json -> "external_tools")
        # ====================================================
        ext_tools = self.environment.get("external_tools", {})
        self.cmd_script_path = self.resolve_json_path(ext_tools.get("sound2wem_cmd"), root_dir, must_exist=True)

        # --- PROMPT ASSETS & FILES ---
        files = self.llm_prompting.get("files", {})
        # self.csv_path = self.resolve_json_path(files.get("csv_path"), root_dir, must_exist=True) # CSV for intent mapping
        # self.intent_map = self.load_intent_map(self.csv_path) # CSV for intent mapping
        self.transcripts_path = self.resolve_json_path(files.get("transcripts_path"), root_dir, must_exist=True) # JSON for intent mapping
        self.intent_map = json.loads(self.transcripts_path.read_text(encoding="utf-8")) # JSON for intent mapping

        self.suit_voice_base_path = self.resolve_json_path(files.get("base_prompt"), root_dir, must_exist=True)
        self.suit_voice_base = self.suit_voice_base_path.read_text(encoding="utf-8")

        self.suit_voice_dynamic_path = self.resolve_json_path(files.get("dynamic_prompt"), root_dir, must_exist=True)
        self.suit_voice_dynamic = self.suit_voice_dynamic_path.read_text(encoding="utf-8")

        self.suit_voice_combat_path = self.resolve_json_path(files.get("combat_prompt"), root_dir, must_exist=True)
        self.suit_voice_combat = self.suit_voice_combat_path.read_text(encoding="utf-8")

        self.tokenized_logits_path = self.resolve_json_path(files.get("tokenized_logits_path"), root_dir, must_exist=True)
        self.logit_banlist = json.loads(self.tokenized_logits_path.read_text(encoding="utf-8"))

        # --- COMBAT / CATEGORY METRIC SETTING ---
        combat_cfg = self.llm_prompting.get("combat", {})
        self.milcat_enable_reasoning = combat_cfg.get("allow_reasoning", True)
        self.mil_cat = combat_cfg.get("special_categories", [])

        labels = self.llm_prompting.get("category_labels", {})
        self.units_received = labels.get("units_received", "Increased Funds")
        self.units_insufficient = labels.get("units_insufficient", "Insufficient Funds")

        # --- USER PROFILE & CUSTOMIZATION ---
        self.player_name = self.customization.get("player_name", "Interloper")
        phrase_settings = self.customization.get("phrase_settings", {})
        # --- Inside your Config Class Initialization ---
        self.promptdata_path = self.resolve_json_path(files.get("prompt_data"), root_dir, must_exist=True)
        raw_prompt_json = json.loads(self.promptdata_path.read_text(encoding="utf-8"))

        # Create a structured memory object for the Tkinter UI to read descriptions
        self.ui_promptdata = raw_prompt_json

        # Flatten the dictionary dynamically in memory for the backend AI engine!
        # This keeps the rest of your text generation loops 100% stable and untouched.
        self.promptdata = {
            "wordiness": {
                key: (val["prompt"] if isinstance(val, dict) else val)
                for key, val in raw_prompt_json.get("wordiness", {}).items()
            },
            "tones": {
                key: (val["prompt"] if isinstance(val, dict) else val)
                for key, val in raw_prompt_json.get("tones", {}).items()
            }
        }

        # Keep your existing state trackers exactly as they are
        self.current_tone = phrase_settings.get("tone", "Standard")
        self.current_wordiness = phrase_settings.get("wordiness", "Standard")


        # Audio effect mapping dict for processing pipeline reference
        self.voice_effects = self.customization.get("voice_effects", {})

        # FFMPEG Binary Resolution
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            # Fall back to alternative platform configuration options if explicitly added
            ffmpeg_env = self.environment.get("external_tools", {}).get("ffmpeg_path")
            if ffmpeg_env:
                ffmpeg_path = Path(ffmpeg_env.strip('"'))
                os.environ["PATH"] = str(ffmpeg_path.parent) + ";" + os.environ.get("PATH", "")
            else:
                raise SystemExit("ffmpeg not found on PATH. Please install ffmpeg or set up path contexts.")
        self.ffmpeg_path = Path(ffmpeg_path)

        # wwise settings
        env_var = self.dsv2wem.get(
            "wwise_root_windows_environment_variable",
            "WWISEROOT"
        ) # Because future me will ask where WWISEROOT is defined, forget that it's a Windows environment variable, and spend 30 minutes searching the repo.
        self.wwise_root = os.environ.get(env_var)

        if not self.wwise_root:
            raise SystemExit(
                 f"DEBUG TOKEN = DSV2WEM_WWISE >> Windows environment variable '{env_var}' not found."
            )

        self.wwise_console_path = (
            Path(self.wwise_root)
            / "Authoring"
            / "x64"
            / "Release"
            / "bin"
            / "WwiseConsole.exe"
        )

        if not self.wwise_console_path.exists():
            raise SystemExit(
                "DEBUG TOKEN = DSV2WEM_WWISE >> WwiseConsole.exe not found."
            )

        self.project_path = self.dsv2wem.get("project_path", "sound2wem")
        self.project_name = self.dsv2wem.get("project_name", "wavtowemscript")
        self.project_file_name = self.dsv2wem.get("project_file", "wavtowemscript.wproj")
        self.project_file_path = Path(self.project_path) / self.project_name / self.project_file_name
        self.conversion_profile = self.dsv2wem.get("conversion_profile", "Vorbis Quality High")

        # --- ML MODEL INITIALIZATIONS ---
        models = self.environment.get("models", {})

        # Coqui-TTS Lazy Loading Setup
        self.tts_model_name = models.get("tts_model")
        if not self.tts_model_name:
            raise ValueError("tts_model token signature missing inside configuration targets.")

        # Explicit type hint tells Pylance that TTS is allowed here later!
        self.tts_model: Optional[TTS] = None

        # Llama Engine Setup
        self.llm_model = str(self.resolve_json_path(models.get("llm_model"), root_dir, must_exist=True))
        self.llm = None  # You can also use self.llm: Optional[Llama] = None if it squawks here too
        if init_llm:
            self.llm = Llama(
                model_path=self.llm_model,
                n_ctx=40960,
                n_batch=1024,
                n_threads=4,
                verbose=False
            )

        self.recent_lines_text = {}  # Runtime session state cache tracker: {wem_id_str: [line1, line2, ...]}

    def get_tone(self) -> str:
        return self.current_tone or "Standard"

    def get_wordiness(self, category: str) -> str:
        if category in self.mil_cat:
            return "Observer"
        return self.current_wordiness or "Standard"

    def resolve_json_path(self, path_str: str, root: Path, must_exist=True) -> Path:
        if not path_str:
            raise ValueError("Required configuration path entry is missing in JSON targets.")

        p = Path(path_str.strip('"'))
        if not p.is_absolute():
            p = root / p

        if must_exist and not p.exists():
            raise FileNotFoundError(f"Configuration file element targets a missing path reference: {p}")
        return p

    @staticmethod # OBSOLETE, REMOVED: Use load_json() instead for JSON files
    def load_intent_map(csv_path: Path) -> dict:
        i_intent_map = {}
        if not csv_path.exists():
            return i_intent_map
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    wem_number = (row.get('WEM_number') or '').strip()
                    i_intent_map[wem_number] = {
                        "Transcription": (row.get('Transcription') or '').strip(),
                        "Category": (row.get('Category') or '').strip(),
                        "Intent": (row.get('Intent') or '').strip(),
                    }
        except Exception as e:
            print(f"Error loading intent map CSV profile: {e}")
        return i_intent_map
