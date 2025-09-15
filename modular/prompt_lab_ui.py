# prompt_lab_ui.py
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font

from pathlib import Path

class PromptLabUI:
    def __init__(self, config, intent_map, process_entry_fn, process_single_all_fn=None):
        """
        config: instance of SuitVoiceConfig (must have .promptbuilder (dict) and optionally .promptbuilder_path (Path))
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

        self.process_entry = process_entry_fn
        self.process_single_all = process_single_all_fn

        # backend data
        self.promptbuilder = config.promptbuilder  # live dict
        self.promptbuilder_path = getattr(config, "promptbuilder_path", None)

        # prepare lists
        self.categories = list(self._collect_categories())
        self.tones = list(self.promptbuilder.get("tones", {}).keys())
        self.wordiness_levels = list(self.promptbuilder.get("wordiness", {}).keys())

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

    def _on_wem_selected(self, event=None):
        wem_selection = self.wem_var.get()
        wem_id = wem_selection.split("|")[0].strip() if "|" in wem_selection else wem_selection
        entry = self.intent_map.get(wem_id)
        if not entry:
            return

        # fill editable fields
        self.trans_var.set(entry.get("Transcription", ""))
        self.category_field_var.set(entry.get("Category", ""))
        self.intent_var.set(entry.get("Intent", ""))
        self.context_var.set(entry.get("Context", ""))
        self._log(f"Selected WEM {wem_id}")

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
        # promptbuilder may mix strings and dicts at top level. gather keys except 'tones'/'wordiness'
        for k in self.promptbuilder.keys():
            if k not in ("tones", "wordiness", "Default", "Unused"):
                yield k
        # always include Default
        if "Default" in self.promptbuilder:
            yield "Default"

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
        ttk.Label(frm_top, text="Category").grid(row=0, column=0, sticky="w")
        self.category_var = tk.StringVar(value=self.categories[0] if self.categories else "Default")
        self.category_cb = ttk.Combobox(frm_top, values=self.categories, textvariable=self.category_var, width=30)
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

        # bind selection
        self.wem_cb.bind("<<ComboboxSelected>>", self._on_wem_selected)

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

        # Left column: category prompt
        left = ttk.Frame(pnl)
        left.pack(side="left", fill="both", expand=True, padx=(0,6))

        ttk.Label(left, text="Category Prompt (editable)").pack(anchor="w")
        self.cat_text = scrolledtext.ScrolledText(left, height=5, wrap="word", **text_cfg)
        self.cat_text.pack(fill="x")
        ttk.Button(left, text="Save Category Prompt", command=self._save_category_prompt).pack(anchor="e", pady=(6,0))

        # Middle column: wordiness
        mid = ttk.Frame(pnl)
        mid.pack(side="left", fill="both", expand=True, padx=(0,6))

        ttk.Label(mid, text="Wordiness Prompt (editable)").pack(anchor="w")
        self.word_text = scrolledtext.ScrolledText(mid, height=5, wrap="word", **text_cfg)
        self.word_text.pack(fill="x")
        ttk.Button(mid, text="Save Wordiness Prompt", command=self._save_wordiness_prompt).pack(anchor="e", pady=(6,0))

        # Right column: tone
        right = ttk.Frame(pnl)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(right, text="Tone Prompt (editable)").pack(anchor="w")
        self.tone_text = scrolledtext.ScrolledText(right, height=5, wrap="word", **text_cfg)
        self.tone_text.pack(fill="x")
        ttk.Button(right, text="Save Tone Prompt", command=self._save_tone_prompt).pack(anchor="e", pady=(6,0))
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
        ttk.Button(frm_footer, text="Save Promptbuilder JSON As...", command=self._save_as).pack(side="left")
        ttk.Button(frm_footer, text="Clear Log", command=lambda: self.log.delete('1.0', tk.END)).pack(side="left", padx=(6,0))
        ttk.Button(frm_footer, text="Quit", command=self.root.destroy).pack(side="right")

        # initial load into editors
        self._populate_editors()

    def _reload_prompts(self):
        # reload the prompting JSON if path exists
        if self.promptbuilder_path and Path(self.promptbuilder_path).exists():
            with open(self.promptbuilder_path, encoding="utf-8") as f:
                self.promptbuilder = json.load(f)
                self.config.promptbuilder = self.promptbuilder
            self.categories = list(self._collect_categories())
            self.tones = list(self.promptbuilder.get("tones", {}).keys())
            self.wordiness_levels = list(self.promptbuilder.get("wordiness", {}).keys())
            self._populate_editors()
            self._log("Reloaded promptbuilder from disk.")
        else:
            self._log("No promptbuilder_path set; using in-memory prompts.")

    def _populate_editors(self):
        cat = self.category_var.get()
        # category context could be string or dict; handle both
        category_context = self.promptbuilder.get(cat, self.promptbuilder.get("Default", ""))
        if isinstance(category_context, dict):
            # if it's dict, try to get a human-readable default key
            cat_text = category_context.get("Default", json.dumps(category_context, indent=2))
        else:
            cat_text = str(category_context)
        self.cat_text.delete('1.0', tk.END)
        self.cat_text.insert(tk.END, cat_text)

        # wordiness
        w = self.wordiness_var.get()
        w_text = self.promptbuilder.get("wordiness", {}).get(w, "")
        self.word_text.delete('1.0', tk.END)
        self.word_text.insert(tk.END, w_text)

        # tone
        t = self.tone_var.get()
        tone_key = t if t != "Random" else self.tones[0] if self.tones else ""
        t_text = self.promptbuilder.get("tones", {}).get(tone_key, "")
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
        self.promptbuilder[cat] = new
        self.config.promptbuilder = self.promptbuilder
        self._persist_promptbuilder()
        self._log(f"Saved Category prompt for '{cat}'")

    def _save_wordiness_prompt(self):
        w = self.wordiness_var.get()
        new = self.word_text.get('1.0', tk.END).strip()
        if not new:
            messagebox.showwarning("Empty", "Wordiness prompt is empty, aborting save.")
            return
        if "wordiness" not in self.promptbuilder:
            self.promptbuilder["wordiness"] = {}
        self.promptbuilder["wordiness"][w] = new
        self.config.promptbuilder = self.promptbuilder
        self._persist_promptbuilder()
        self._log(f"Saved Wordiness prompt for '{w}'")

    def _save_tone_prompt(self):
        t = self.tone_var.get()
        if t == "Random":
            messagebox.showwarning("Tone selection", "Random is not editable; pick a concrete tone first.")
            return
        new = self.tone_text.get('1.0', tk.END).strip()
        if not new:
            messagebox.showwarning("Empty", "Tone prompt is empty, aborting save.")
            return
        if "tones" not in self.promptbuilder:
            self.promptbuilder["tones"] = {}
        self.promptbuilder["tones"][t] = new
        self.config.promptbuilder = self.promptbuilder
        self._persist_promptbuilder()
        self._log(f"Saved Tone prompt for '{t}'")

    def _persist_promptbuilder(self):
        # write back to file if path available
        if not self.promptbuilder_path:
            self._log("No promptbuilder_path available in config; changes saved in memory only.")
            return
        try:
            with open(self.promptbuilder_path, "w", encoding="utf-8") as f:
                json.dump(self.promptbuilder, f, indent=2, ensure_ascii=False)
            self._log(f"Persisted promptbuilder to {self.promptbuilder_path}")
        except Exception as e:
            self._log(f"Error persisting promptbuilder: {e}")

    def _save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.promptbuilder, f, indent=2, ensure_ascii=False)
            self._log(f"Saved promptbuilder copy to {p}")
        except Exception as e:
            self._log(f"Error saving: {e}")

    def _update_preview(self):
        pass

    def _log(self, s):
        self.log.insert(tk.END, s + "\n")
        self.log.see(tk.END)

    def _on_generate(self):
        # gather params and call process_entry in background
        wem_selection = self.wem_var.get()
        wem_id = wem_selection.split("|")[0].strip() if "|" in wem_selection else wem_selection

        if not wem_id:
            messagebox.showwarning("WEM ID", "Please select a WEM ID.")
            return

        wordiness = self.wordiness_var.get()
        tone = self.tone_var.get()
        if tone == "Random":
            import random
            tone = random.choice(list(self.promptbuilder.get("tones", {}).keys()))

        # run in background so UI doesn't block
        thr = threading.Thread(target=self._run_generation, args=(wem_id,), daemon=True)
        thr.start()

    def _on_run_all_tones(self):
        wem_id = str(self.wem_var.get()).strip()
        if not wem_id:
            messagebox.showwarning("WEM ID", "Please provide a WEM ID.")
            return
        # if user provided a helper to run single-wem across tones, use it; else brute-force
        thr = threading.Thread(target=self._run_all_tones_thread, args=(wem_id,), daemon=True)
        thr.start()

    def _run_all_tones_thread(self, wem_id):
        tones = list(self.promptbuilder.get("tones", {}).keys())
        for tone in tones:
            self._log(f"--- Tone: {tone} ---")
            self._run_generation(wem_id)

    def _run_generation(self, wem_id):
        wem_id_str = str(wem_id)
        entry = self.intent_map.get(wem_id_str)
        if not entry:
            self._log(f"WEM {wem_id_str} not found in intent map.")
            return
        try:
            # call process_entry; it's expected to return (wem_id, reworded)
            print(f"passed in tone: {self.config.current_tone}")
            res = self.process_entry(wem_id_str, entry, self.config.current_wordiness, self.config.current_tone)
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
