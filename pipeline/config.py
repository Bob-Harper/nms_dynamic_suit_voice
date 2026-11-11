# config.py
import json
import os
import shutil
import sys
from pathlib import Path
from llama_cpp import Llama, Optional

from .debug_support import record_exception

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
        # Anchor to project root (parent of pipeline/)
        root_dir = Path(__file__).parent.parent
        config_dir = root_dir / "config"
        self.project_root = root_dir
        # Load file structures
        self.default_environment = load_json(config_dir / "default_environment_config.json")
        self.environment = load_json(config_dir / "environment_config.json")
        self.default_customization = load_json(config_dir / "default_customization.json")
        self.user_customization = load_json(config_dir / "user_customization.json")

        # --- CENTRALIZED PROJECT METADATA ---
        project_meta = self.environment.get("project", {})
        v_num = project_meta.get("version", "Something")
        v_major = project_meta.get("release_major", "Went")
        v_minor = project_meta.get("release_minor", "Wrong")
        self.project_url = project_meta.get("base_url", "https://github.com/Bob-Harper/nms_dynamic_suit_voice")
        support_path = project_meta.get("support", "issues")
        # Cleanly join the base repository link with the support subdirectory target
        self.support_url = f"{self.project_url.rstrip('/')}/{support_path}"
        # Compiles to schema example: "v1.2.2 (Unchained.QT)"
        self.version_signature = f"v{v_num} ({v_major}.{v_minor})"

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

        # System tray icon path used by the Qt control deck
        icon_path_obj = self.resolve_json_path(paths.get("icon_image"), root_dir, must_exist=True)
        self.icon_image = str(icon_path_obj)

        # Engine Cache Locations (Will be auto-provisioned safely below)
        self.temp_wem_dir = self.resolve_json_path(paths.get("temp_wem_dir"), root_dir, must_exist=False)
        self.temp_wav_dir = self.resolve_json_path(paths.get("temp_wav_dir"), root_dir, must_exist=False)
        self.quick_cache_dir = self.resolve_json_path(paths.get("quick_cache_dir"), root_dir, must_exist=False)

        # Logging for Debug interface
        self.debug_reports_path = self.resolve_json_path(
            paths.get("debug_reports_label", "logs/debug_reports.jsonl"),
            root_dir,
            must_exist=False
        )

        # Window platform subprocess flags
        self.create_no_window = 0x08000000 if sys.platform == "win32" else 0

        # Enforce workspace directories (Safe loop: all paths are strict non-nullable Path types)
        for d in [self.temp_wem_dir, self.temp_wav_dir, self.quick_cache_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # --- PROMPT ASSETS & FILES ---
        prompting_config_path = self.resolve_json_path(
            paths.get("llm_prompting_config", "data/llm_prompting.json"),
            root_dir,
            must_exist=True
        )
        self.llm_prompting = load_json(prompting_config_path)


        files = self.llm_prompting.get("files", {})

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

        # Create structured descriptions for the Qt control deck
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

        # ====================================================
        # EXTERNAL TOOLS INFRASTRUCTURE
        # ====================================================
        external_tools = self.environment.get("external_tools", {})

        # Resolve the unified assets installation directory folder path cleanly
        self.wav2wem_assets_dir = self.resolve_json_path(
            external_tools.get("wav2wem_assets", "assets/wav2wem/assets/"),
            root_dir,
            must_exist=True
        )
        # Build absolute system tracks for all associated tool binaries
        self.wav2wem_binary_path = self.wav2wem_assets_dir / "wav2wem.exe"
        self.ogg_encoder_path = self.wav2wem_assets_dir / "oggenc2.exe"

        # --- ML MODEL INITIALIZATIONS ---
        models = self.environment.get("models", {})
        model_url = self.environment.get("model_url", {})

        # Wrapping this in Path()
        self.tts_base_dir = Path(paths.get("tts_base_dir", "assets/weights").strip('"'))

        # --- TTS Model ---
        self.tts_model_name = models.get("tts_model")
        if not self.tts_model_name:
            raise ValueError("DEBUG TOKEN = TTSMODEL_SIG >> tts_model token signature missing inside configuration targets.")

        self.tts_voice_bin = self.tts_base_dir / models.get("tts_voice_bin", "voices-v1.0.bin")
        self.tts_model = self.tts_base_dir / models.get("tts_model", "kokoro-v1.0.fp16.onnx")

        # Centralize core network release endpoints for download passes later
        self.tts_base_url = model_url.get("tts_base_url", "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1")

        # Llama Engine Setup
        self.llm_model = str(self.resolve_json_path(models.get("llm_model"), root_dir, must_exist=True))
        self.llm = None
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
            raise ValueError("DEBUG TOKEN = JSONCONFIG_NR >> Required configuration path entry is missing in JSON targets.")

        p = Path(path_str.strip('"'))
        if not p.is_absolute():
            p = root / p

        if must_exist and not p.exists():
            raise FileNotFoundError(f"DEBUG TOKEN = JSONCONFIG_NP >> Configuration file element targets a missing path reference: {p}")
        return p

    @staticmethod
    def get_version_signature() -> str:
        """
        Globally accessible static hook. Allows the UI launcher, README tools,
        or update checkers to grab the single source of truth version instantly.
        """
        try:
            config_dir = Path(__file__).parent.parent / "config"
            with open(config_dir / "environment_config.json", "r", encoding="utf-8") as f:
                env = json.load(f)
            meta = env.get("project", {})
            return f"v{meta.get('version', 'Something')} ({meta.get('release_major', 'Went')}.{meta.get('release_minor', 'Wrong')})"
        except Exception as error:
            token = record_exception(error, "Reading the configured application version")
            return f"Configuration version could not be read. DEBUG TOKEN = {token}"