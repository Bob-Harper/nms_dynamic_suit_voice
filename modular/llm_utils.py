import time
import re


def create_logit_bias(config, category_l):
    logit_bias = {
        **extract_token_ids(config.logit_banlist.get(category_l, {})),
        **extract_token_ids(config.logit_banlist.get("Default", {})),
    }  # to add more categorys like Encouraged or Discouraged with different scores use Default as template
    return logit_bias


def extract_token_ids(data: dict):
    """Flatten token dict and ignore non-integer keys like 'bias'."""
    return {int(k): v for k, v in data.get("tokens", {}).items()}


def reword_phrase(config, wem_id_r,
                  category_r,
                  original_phrase_r,
                  finalprompt):
    # enforce usage or avoidance of specific tokens using logits
    logit_bias_list = create_logit_bias(config, category_r)

    messages = [{"role": "system", "content": finalprompt}]
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # print(f"Raw Input:\n {messages}")
            output = config.llm.create_chat_completion(
                messages=messages,
                max_tokens=4096,  # less can be faster but can cut off thinking, breaking the result
                temperature=0.75,
                top_k=90,
                top_p=0.9,
                repeat_penalty=1.25,
                logit_bias=logit_bias_list,
                seed=-1  # must add this to randomize the results
            )
            # print(f"Raw Output:\n {output}")
            result = output["choices"][0]["message"]["content"].strip()
            result = postprocess_units(config, result, category_r)
            result = postprocess_for_tts(result)
            return result

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e}")
                return f"WEM ERROR {wem_id_r}, {e}. {original_phrase_r}"
    print(f"ERROR on WEM {wem_id_r}")
    return f"External Reality Failure. {original_phrase_r}"


def postprocess_units(config, text: str, category: str) -> str:
    # Check if this category matches your in-game currency categories
    if category == config.units_received or category == config.units_insufficient:
        # Replace "Funds" with "Units" safely
        text = text.replace("Funds", "Units").replace("funds", "Units")
    return text

def postprocess_for_tts(text: str) -> str:
    # Existing cleanup
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Strip Thinking
    text = re.sub(r"[—–]", ", ", text)  # convert em-dash / en-dash

    # --- Kernel-safe additions ---
    text = text.rstrip("*")              # remove trailing asterisks
    text = text.replace("\n*", "\n")    # fix newline + asterisk
    text = text.replace("\r*", "\r")
    text = text.strip()                  # final strip of whitespace

    if not text.endswith("."):           # optional safe sentence ending
        text += "."

    return text
