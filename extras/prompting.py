# prompting.py
import json


class CategoryPrompts:
    def __init__(self, json_path="data/category_prompts.json"):
        with open(json_path, encoding="utf-8") as file:
            self.prompts = json.load(file)

    def get_prompt(self, category: str) -> str:
        """Return the formatted prompt based on category_for_logit, or fallback."""

        context = self.prompts.get(category, self.prompts.get("Default"))
        return f"{context}"

