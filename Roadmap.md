# NMS Dynamic Suit Voice — Master Roadmap & Architecture Goals

## 1. Granular Cache Manager Panel
- **Per-WEM Rule Overrides:** Toggle `Used` status (Yes/No), set individual rolling cache limits (e.g., 4 vs. 16), or disable caching entirely per ID.
- **Manual Generation Controls:**
  - Top up a single selected WEM ID to its max limit or a custom typed value.
  - Global batch top-up button ("Fill All") to populate all active IDs to configured maximums.
- **File & Storage Telemetry:**
  - Display file counts and disk space usage per WEM ID and across the entire cache batch.
  - Interactive list of generated `.wem` files in each directory with highlight-and-delete functionality (strictly no playback preview).
- **No audio Preview for Existing Files:** No Audio Preview, never an audio preview - the whole point is for every line to be unique; never heard before, never heard again.

## 2. Prompt Workbench & Customization Engine
- **Complete Prompt Exposure:** Expose system prompts, categories, intents, and modifiers in a dedicated UI panel.
- **Integrated Testing:** Recycle the existing voice preview sandbox pipeline to test prompt rewording and LLM interpretations through a streamlined pipeline, with options to save text and/or wav outputs.
- **Per-Model Prompt Profiles:** Save and load prompt configurations tied to specific LLM models so switching models preserves custom tuning.
- **User-Defined Matrices & Localization:**
  - Allow users to create and add custom styles, wordiness levels, and personality matrices.
  - Build structural support for multi-language localization.

## 3. Non-Destructive Configuration & System Transparency
- **Safe Config Migrations:**
  - Automatically detect older `user_customization.json` or `environment_config.json` files on startup.
  - preserve all existing user tweaks while initializing newly added features with safe baseline defaults.
  - Already does, but worth repeating to ensure this remains a primary focus
  - ensure and even insist on out-of-project backup locations to ensure user configs survive updates..
- **Config Inspector Page:** A read-only transparency view displaying the exact merged configuration state currently active in memory, selectable user vs system view.
- **System & Path Settings UI:** Expose core directory paths, runtime intervals, and all system config settings directly in the interface behind the "do not unless you know what you are doing".

## 4. Unified Model Management & One-Stop Launcher
- **LLM Model Manager:** Expand model management beyond TTS to handle local LLM downloads, precision selection, and active switching.
- **Self-Updater (ComfyUI-Style):** Built-in `git pull` integration already there. Expand with a requirements/package manager to update dependencies from the UI either individually or by rerunning requirements.txt.
- **Direct Game Launcher:**
  - Configure the path to `NMS.exe` and optional CLI startup arguments for power users.
  - One-click launch trigger directly inside the DSV Manager to turn the app into a complete, all-in-one launchpad.
  - No there are no plans to have this handle other people's mods.  this one is more than enough for me, if you want a mod manager - i would suggest the one provide by the wonderful folks at nexusmods.com

