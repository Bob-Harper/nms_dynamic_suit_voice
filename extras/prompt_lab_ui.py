# prompt_lab_ui.py
from modular.config import SuitVoiceConfig
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font
import time
from modular.llm_utils import reword_phrase
from modular.prompt_utils import build_suit_prompt

from pathlib import Path
config = SuitVoiceConfig()


class PromptLabUI:
    def __init__(self, config, intent_map, process_single_all_fn=None):
        """
        config: instance of SuitVoiceConfig (must have .promptdata (dict) and optionally .promptdata_path (Path))
        intent_map: dict loaded from load_intent_map(config.csv_path)
        process_entry_fn: function signature process_entry(wem_id, entry, wordiness_level="Standard", tone="Standard")
        process_single_all_fn (optional): convenience function to run single WEM across all tones
        """
        self.config = config
        self.intent_map = intent_map
        # Build a human-readable list for the WEM combobox
        self.wem_options = [
            f"{wem_id} | {entry['Category']} | {entry['Intent']}"
            for wem_id, entry in self.intent_map.items()
        ]

        self.process_single_all = process_single_all_fn

        # backend data
        self.promptdata = config.promptdata  # live dict
        self.promptdata_path = getattr(config, "promptdata_path", None)

        # prepare lists
        self.category_list = list(self._collect_categories())
        self.tones = list(self.promptdata.get("tones", {}).keys())
        self.wordiness_levels = list(self.promptdata.get("wordiness", {}).keys())

        # defaults
        if "Standard" not in self.wordiness_levels:
            self.wordiness_levels.insert(0, "Standard")
        if "Standard" not in self.tones:
            self.tones.insert(0, "Standard")

        # build UI
        self.root = tk.Tk()
        self.root.title("Suit Prompt Lab")
        self._build_ui()

        self.wem_options.sort()
        self._update_wem_dropdown()

        self._reset_fields()

    @staticmethod
    def process_entry(wem_id, entry, wordiness_level="Standard", tone="Standard"):
        """Shared processing of a single intent-map entry."""
        config.current_tone = tone  # <— refresh tone
        category = entry["Category"]
        original_phrase = entry["Transcription"]
        intent = entry["Intent"]

        # Build the structured prompt
        finalprompt = build_suit_prompt(config, category, intent, original_phrase, wem_id)
        # convert Player Name Placeholder
        finalprompt = finalprompt.format(
            name=config.player_name.strip(),
        )
        # print(f"final prompt: {finalprompt}")
        start_time = time.time()
        try:
            # Generate with LLM
            reworded = reword_phrase(config, wem_id, original_phrase, intent, finalprompt)

            print(f"\nWEM: {wem_id} -- Original Game Wording: {original_phrase}")
            print(f"Tone: ({tone}) Verbosity: ({wordiness_level})")
            print(f"\033[92mFinal Output: {reworded}\033[0m")

        except Exception as e:
            print(f"LLM ERROR on WEM {wem_id}: {e}")
            reworded = f"WEM ERROR {wem_id}.  {original_phrase}"

        elapsed = time.time() - start_time
        print(f"Processing time for WEM {wem_id}: {elapsed:.2f} seconds")

        return wem_id, reworded

    def _process_by_category(self, target_category, wordiness_level="Standard", tone="Standard"):
        for wem_id, entry in self.intent_map.items():
            if entry.get("Category") != target_category:
                continue
            yield self.process_entry(wem_id, entry, wordiness_level, tone)

    def _run_category_batch(self, category, wordiness, tone):
        count = self.loop_count_var.get()
        for i in range(count):
            self._log(f"Loop {i + 1}/{count} for category '{category}' | Tone: {tone} | Wordiness: {wordiness}")
            try:
                for wem_id, reworded in self._process_by_category(category, wordiness, tone):
                    self._log(f"{wem_id}: {reworded}")
            except Exception as e:
                self._log(f"Error during category batch: {e}")
        self._log(f"Batch generation complete for category '{category}'")

    def _on_wem_selected(self, event=None):
        wem_selection = self.wem_var.get()
        wem_id = wem_selection.split("|")[0].strip() if "|" in wem_selection else wem_selection
        entry = self.intent_map.get(wem_id)
        if not entry:
            return

        self.trans_var.set(entry.get("Transcription", ""))
        self.category_field_var.set(entry.get("Category", ""))
        self._populate_editors()
        self.intent_var.set(entry.get("Intent", ""))
        self.context_var.set(entry.get("Context", ""))

        # Populate context from promptdata if available
        cat = entry.get("Category", "")
        context_text = self.promptdata.get(cat, "")
        self.context_var.set(str(context_text))
        cat_data = self.promptdata.get(cat, {})
        if isinstance(cat_data, dict):
            self.context_var.set(cat_data.get("Standard", ""))
        context = self.config.promptdata.get(cat, "")
        self.context_var.set(context)

        self._log(f"Selected WEM {wem_id}")

    def _on_category_selected(self, event=None):

        self.wem_var.set("")
        self.trans_var.set("")
        self.intent_var.set("")
        self.category_field_var.set("")
        self.context_var.set("")

        # Update editable prompt window
        self._populate_editors()

        batch_category = self.category_var.get()
        context_text = self.promptdata.get(batch_category, "")
        self.context_var.set(str(context_text))

        cat_data = self.promptdata.get(batch_category, {})
        if isinstance(cat_data, dict):
            self.context_var.set(cat_data.get("Standard", ""))
        else:
            self.context_var.set("")

        self._log(f"Category selected: {batch_category}")

    def _save_csv_fields(self):
        wem_selection = self.wem_var.get()
        wem_id = wem_selection.split("|")[0].strip() if "|" in wem_selection else wem_selection
        if wem_id not in self.intent_map:
            self._log(f"WEM {wem_id} not found, cannot save")
            return

        self.intent_map[wem_id]["Transcription"] = self.trans_var.get()
        self.intent_map[wem_id]["Category"] = self.category_field_var.get()
        self.intent_map[wem_id]["Intent"] = self.intent_var.get()
        self.intent_map[wem_id]["Context"] = self.context_var.get()

        self._log(f"Saved CSV fields for WEM {wem_id}")

        # refresh dropdown to reflect updated Category / Intent
        self._update_wem_dropdown()

    def _update_wem_dropdown(self):
        # Build display list: "WEM_number | Category | Intent"
        wem_list = [
            f"{wem}|{self.intent_map[wem].get('Category', '')}|{self.intent_map[wem].get('Intent', '')}"
            for wem in sorted(self.intent_map.keys())
        ]
        self.wem_cb['values'] = wem_list

        # preserve current selection if possible
        current = self.wem_var.get()
        if current not in wem_list:
            self.wem_var.set(wem_list[0] if wem_list else "")

    def _collect_categories(self):
        # promptdata may mix strings and dicts at top level. gather keys except 'tones'/'wordiness'
        for k in self.promptdata.keys():
            if k not in ("tones", "wordiness", "Standard", "Unused"):
                yield k
        # always include Default
        if "Standard" in self.promptdata:
            yield "Standard"

    def _reset_fields(self):
        self.category_var.set("")
        self.wem_var.set("")
        self.trans_var.set("")
        self.category_field_var.set("")
        self.intent_var.set("")
        self.context_var.set("")
        self.wordiness_var.set("Standard")
        self.tone_var.set("Standard")
        self._populate_editors()
        self._log("Fields reset.")

    def _build_ui(self):
        # Example: 12pt instead of tiny defaults
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=12)
        # after you configure TkDefaultFont, add a text style font
        text_font = font.nametofont("TkTextFont")
        text_font.configure(size=12, family="Consolas")  # or another clean font
        self.root.configure(bg="#2b2b2b")
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
        frm_top = ttk.Frame(self.root)
        frm_top.pack(fill="x", padx=pad, pady=pad)

        # Category
        ttk.Label(frm_top, text="Prompting Category").grid(row=0, column=0, sticky="w")
        self.category_var = tk.StringVar(value=self.category_list[0] if self.category_list else "")
        self.category_cb = ttk.Combobox(frm_top, values=self.category_list, textvariable=self.category_var, width=30)
        self.category_cb.grid(row=0, column=1, sticky="w", padx=(4, 12))

        # Wordiness
        ttk.Label(frm_top, text="Wordiness").grid(row=0, column=2, sticky="w")
        self.wordiness_var = tk.StringVar(value=self.wordiness_levels[0] if self.wordiness_levels else "Standard")
        self.wordiness_cb = ttk.Combobox(frm_top, values=self.wordiness_levels, textvariable=self.wordiness_var, width=18)
        self.wordiness_cb.grid(row=0, column=3, sticky="w", padx=(4, 12))

        # Tone
        ttk.Label(frm_top, text="Tone").grid(row=0, column=4, sticky="w")
        tone_choices = ["Random"] + self.tones
        self.tone_var = tk.StringVar(value="Random")
        self.tone_cb = ttk.Combobox(frm_top, values=tone_choices, textvariable=self.tone_var, width=22)
        self.tone_cb.grid(row=0, column=5, sticky="w", padx=(4, 12))

        # WEM ID entry
        ttk.Label(frm_top, text="WEM ID").grid(row=1, column=0, sticky="w")
        self.wem_var = tk.StringVar()
        self.wem_cb = ttk.Combobox(frm_top, textvariable=self.wem_var, width=40)
        self.wem_cb.grid(row=1, column=1, sticky="w", padx=(4, 12))

        # populate values immediately
        self._update_wem_dropdown()
        ttk.Button(frm_top, text="Show Prompt Only", command=self._on_show_prompt).grid(row=0, column=6, padx=5)
        ttk.Button(frm_top, text="Reset Fields", command=self._reset_fields).grid(row=1, column=6, padx=(8, 0))

        ttk.Label(frm_top, text="Loop Count").grid(row=1, column=7, sticky="w")
        self.loop_count_var = tk.IntVar(value=1)
        ttk.Spinbox(frm_top, from_=1, to=100, textvariable=self.loop_count_var, width=5).grid(row=1, column=8,
                                                                                              sticky="w", padx=(4, 12))
        # bind selection
        self.wem_cb.bind("<<ComboboxSelected>>", self._on_wem_selected)
        self.category_cb.bind("<<ComboboxSelected>>", self._on_category_selected)

        self.all_tones_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm_top, text="All Tones", variable=self.all_tones_var).grid(row=1, column=2, sticky="w")

        btn_gen = ttk.Button(frm_top, text="Generate", command=self._on_generate)
        btn_gen.grid(row=1, column=3, padx=(8,0))

        btn_run_all = ttk.Button(frm_top, text="Run All Tones for WEM", command=self._on_run_all_tones)
        btn_run_all.grid(row=1, column=4, padx=(8,0))

        btn_reload = ttk.Button(frm_top, text="Reload Prompts", command=self._reload_prompts)
        btn_reload.grid(row=1, column=5, padx=(8,0))

        # Separator
        ttk.Separator(self.root).pack(fill="x", pady=(6, 6))

        # Editable prompt panels
        pnl = ttk.Frame(self.root)
        pnl.pack(fill="both", expand=True, padx=pad, pady=pad)

        # Configure 3 equal-width columns
        pnl.columnconfigure(0, weight=1)
        pnl.columnconfigure(1, weight=1)
        pnl.columnconfigure(2, weight=1)

        # Left column: category prompt
        left = ttk.Frame(pnl)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ttk.Label(left, text="Category Prompt (editable)").pack(anchor="w")
        self.cat_text = scrolledtext.ScrolledText(left, height=5, wrap="word", **text_cfg)
        self.cat_text.pack(fill="both", expand=True)
        ttk.Button(left, text="Save Category Prompt", command=self._save_category_prompt).pack(anchor="e", pady=(6, 0))

        # Middle column: wordiness
        mid = ttk.Frame(pnl)
        mid.grid(row=0, column=1, sticky="nsew", padx=(0, 6))

        ttk.Label(mid, text="Wordiness Prompt (editable)").pack(anchor="w")
        self.word_text = scrolledtext.ScrolledText(mid, height=5, wrap="word", **text_cfg)
        self.word_text.pack(fill="both", expand=True)
        ttk.Button(mid, text="Save Wordiness Prompt", command=self._save_wordiness_prompt).pack(anchor="e", pady=(6, 0))

        # Right column: tone
        right = ttk.Frame(pnl)
        right.grid(row=0, column=2, sticky="nsew")

        ttk.Label(right, text="Tone Prompt (editable)").pack(anchor="w")
        self.tone_text = scrolledtext.ScrolledText(right, height=5, wrap="word", **text_cfg)
        self.tone_text.pack(fill="both", expand=True)
        ttk.Button(right, text="Save Tone Prompt", command=self._save_tone_prompt).pack(anchor="e", pady=(6, 0))

        # Frame for CSV fields
        frm_csv = ttk.Frame(frm_top)
        frm_csv.grid(row=2, column=0, columnspan=6, sticky="we", pady=(8, 0))

        # Transcription
        ttk.Label(frm_csv, text="Transcription").grid(row=0, column=0, sticky="w")
        self.trans_var = tk.StringVar()
        self.trans_entry = ttk.Entry(frm_csv, textvariable=self.trans_var, width=60)
        self.trans_entry.grid(row=0, column=1, sticky="we", padx=(4, 12))

        # Category
        ttk.Label(frm_csv, text="Category").grid(row=1, column=0, sticky="w")
        self.category_field_var = tk.StringVar()
        self.category_entry = ttk.Entry(frm_csv, textvariable=self.category_field_var, width=60)
        self.category_entry.grid(row=1, column=1, sticky="we", padx=(4, 12))

        # Intent
        ttk.Label(frm_csv, text="Intent").grid(row=2, column=0, sticky="w")
        self.intent_var = tk.StringVar()
        self.intent_entry = ttk.Entry(frm_csv, textvariable=self.intent_var, width=60)
        self.intent_entry.grid(row=2, column=1, sticky="we", padx=(4, 12))

        # Context
        ttk.Label(frm_csv, text="Context").grid(row=3, column=0, sticky="w")
        self.context_var = tk.StringVar()
        self.context_entry = ttk.Entry(frm_csv, textvariable=self.context_var, width=60)
        self.context_entry.grid(row=3, column=1, sticky="we", padx=(4, 12))

        # Save CSV fields button
        ttk.Button(frm_csv, text="Save CSV Fields", command=self._save_csv_fields).grid(row=4, column=1, sticky="e",
                                                                                        pady=(6, 0))

        # Output / Log
        ttk.Separator(self.root).pack(fill="x", pady=(6, 6))
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="both", expand=True, padx=pad, pady=pad)

        ttk.Label(bottom, text="Output / Log:").pack(anchor="w", pady=(6,0))
        self.log = scrolledtext.ScrolledText(bottom, wrap="word", **text_cfg)
        self.log.pack(fill="both", expand=True)

        # Footer buttons
        frm_footer = ttk.Frame(self.root)
        frm_footer.pack(fill="x", padx=pad, pady=(4,8))
        ttk.Button(frm_footer, text="Save promptdata JSON As...", command=self._save_as).pack(side="left")
        ttk.Button(frm_footer, text="Clear Log", command=lambda: self.log.delete('1.0', tk.END)).pack(side="left", padx=(6,0))
        ttk.Button(frm_footer, text="Quit", command=self.root.destroy).pack(side="right")

        # initial load into editors
        self._populate_editors()

    def _on_show_prompt(self):
        wem_selection = self.wem_var.get().strip()
        wem_id = wem_selection.split("|")[0].strip() if "|" in wem_selection else wem_selection

        if not wem_id:
            messagebox.showwarning("WEM ID", "Please select a WEM ID to preview the prompt.")
            return

        entry = self.intent_map.get(wem_id)
        if not entry:
            self._log(f"WEM {wem_id} not found in intent map.")
            return

        # Sync config with current UI selections
        self.config.current_tone = self.tone_var.get()
        self.config.current_wordiness = self.wordiness_var.get()

        category = entry.get("Category", "")
        intent = entry.get("Intent", "")
        transcription = entry.get("Transcription", "")
        # Build prompt using live pipeline logic
        prompt = build_suit_prompt(self.config, category, intent, transcription, wem_id)
        prompt = prompt.format(name=self.config.player_name.strip())

        self._log(f"Prompt for WEM {wem_id}:\n{prompt}")

    def _reload_prompts(self):
        # reload the prompting JSON if path exists
        if self.promptdata_path and Path(self.promptdata_path).exists():
            with open(self.promptdata_path, encoding="utf-8") as f:
                self.promptdata = json.load(f)
                self.config.promptdata = self.promptdata
            self.categories = list(self._collect_categories())
            self.tones = list(self.promptdata.get("tones", {}).keys())
            self.wordiness_levels = list(self.promptdata.get("wordiness", {}).keys())
            self._populate_editors()
            self._log("Reloaded promptdata from disk.")
        else:
            self._log("No promptdata_path set; using in-memory prompts.")

    def _populate_editors(self):
        cat = self.category_var.get()
        # category context could be string or dict; handle both
        category_context = self.promptdata.get(cat, self.promptdata.get("Standard", ""))
        if isinstance(category_context, dict):
            # if it's dict, try to get a human-readable default key
            cat_text = category_context.get("Standard", json.dumps(category_context, indent=2))
        else:
            cat_text = str(category_context)
        self.cat_text.delete('1.0', tk.END)
        self.cat_text.insert(tk.END, cat_text)

        # wordiness
        w = self.wordiness_var.get()
        w_text = self.promptdata.get("wordiness", {}).get(w, "")
        self.word_text.delete('1.0', tk.END)
        self.word_text.insert(tk.END, w_text)

        # tone
        t = self.tone_var.get()
        tone_key = t if t != "Random" else self.tones[0] if self.tones else ""
        t_text = self.promptdata.get("tones", {}).get(tone_key, "")
        self.tone_text.delete('1.0', tk.END)
        self.tone_text.insert(tk.END, t_text)

        # update preview
        self._update_preview()

    def _save_category_prompt(self):
        cat = self.category_var.get()
        new = self.cat_text.get('1.0', tk.END).strip()
        if not new:
            messagebox.showwarning("Empty", "Category prompt is empty, aborting save.")
            return
        self.promptdata[cat] = new
        self.config.promptdata = self.promptdata
        self._persist_promptdata()
        self._log(f"Saved Category prompt for '{cat}'")

    def _save_wordiness_prompt(self):
        w = self.wordiness_var.get()
        new = self.word_text.get('1.0', tk.END).strip()
        if not new:
            messagebox.showwarning("Empty", "Wordiness prompt is empty, aborting save.")
            return
        if "wordiness" not in self.promptdata:
            self.promptdata["wordiness"] = {}
        self.promptdata["wordiness"][w] = new
        self.config.promptdata = self.promptdata
        self._persist_promptdata()
        self._log(f"Saved Wordiness prompt for '{w}'")

    def _save_tone_prompt(self):
        t = self.tone_var.get()
        if t == "Random":
            messagebox.showwarning("Tone selection", "Random is not editable; pick a concrete tone first.")
            return
        new = self.tone_text.get('1.0', tk.END).strip()
        if not new:
            messagebox.showwarning("Empty", "Tone prompt is empty, aborting save.")
            returndebug_print
        if "tones" not in self.promptdata:
            self.promptdata["tones"] = {}
        self.promptdata["tones"][t] = new
        self.config.promptdata = self.promptdata
        self._persist_promptdata()
        self._log(f"Saved Tone prompt for '{t}'")

    def _persist_promptdata(self):
        # write back to file if path available
        if not self.promptdata_path:
            self._log("No promptdata_path available in config; changes saved in memory only.")
            return
        try:
            with open(self.promptdata_path, "w", encoding="utf-8") as f:
                json.dump(self.promptdata, f, indent=2, ensure_ascii=False)
            self._log(f"Persisted promptdata to {self.promptdata_path}")
        except Exception as e:
            self._log(f"Error persisting promptdata: {e}")

    def _save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.promptdata, f, indent=2, ensure_ascii=False)
            self._log(f"Saved promptdata copy to {p}")
        except Exception as e:
            self._log(f"Error saving: {e}")

    def _update_preview(self):
        pass

    def _log(self, s):
        self.log.insert(tk.END, s + "\n")
        self.log.see(tk.END)

    def _on_generate(self):
        wem_selection = self.wem_var.get().strip()
        category_selection = self.category_var.get().strip()

        wordiness = self.wordiness_var.get()
        tone = self.tone_var.get()
        if tone == "Random":
            import random
            tone = random.choice(list(self.promptdata.get("tones", {}).keys()))

        if wem_selection:
            wem_id = wem_selection.split("|")[0].strip() if "|" in wem_selection else wem_selection
            thr = threading.Thread(target=self._run_generation, args=(wem_id, wordiness, tone), daemon=True)
            thr.start()
        elif category_selection:
            thr = threading.Thread(target=self._run_category_batch, args=(category_selection, wordiness, tone), daemon=True)
            thr.start()
        else:
            messagebox.showwarning("Input Required", "Please select either a WEM ID or a Category.")

    def _on_run_all_tones(self):
        wem_id = str(self.wem_var.get()).strip()
        if not wem_id:
            messagebox.showwarning("WEM ID", "Please provide a WEM ID.")
            return

        wordiness = self.wordiness_var.get()  # <-- Grab current wordiness from UI

        thr = threading.Thread(
            target=self._run_all_tones_thread,
            args=(wem_id, wordiness),
            daemon=True
        )
        thr.start()

    def _run_all_tones_thread(self, wem_id, wordiness):
        tones = list(self.promptdata.get("tones", {}).keys())
        for tone in tones:
            self._log(f"--- Tone: {tone} ---")
            self._run_generation(wem_id, wordiness, tone)

    def _run_generation(self, wem_id, wordiness, tone):
        count = self.loop_count_var.get()
        wem_id_str = str(wem_id)
        entry = self.intent_map.get(wem_id_str)
        if not entry:
            self._log(f"WEM {wem_id_str} not found in intent map.")
            return

        # Set config values so downstream logic sees them
        self.config.current_wordiness = wordiness
        self.config.current_tone = tone

        for i in range(count):
            self._log(f"Run {i + 1}/{count} | Tone: {tone} | Wordiness: {wordiness}")
            try:
                print(f"passed in tone: {tone}")
                res = self.process_entry(wem_id_str, entry, wordiness, tone)
                if isinstance(res, tuple) and len(res) >= 2:
                    _, reworded = res
                else:
                    reworded = str(res)
                self._log(f"Final: {reworded}")
            except Exception as e:
                self._log(f"Error during generation: {e}")

    def run(self):
        # wire change events
        self.category_cb.bind("<<ComboboxSelected>>", lambda e: self._populate_editors())
        self.wordiness_cb.bind("<<ComboboxSelected>>", lambda e: self._populate_editors())
        self.tone_cb.bind("<<ComboboxSelected>>", lambda e: self._populate_editors())
        self.root.mainloop()


intent_map = config.intent_map
ui = PromptLabUI(config, intent_map)
ui.run()
