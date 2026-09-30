import time
from modular.load_env import SuitVoiceConfig

# Load .env vars from load_env.py
config = SuitVoiceConfig()

def reword_phrase(original_phrase_r: str,):
    system_prompt = "Be precise"

    # print(f"Composed System Prompt:\n {system_prompt}")
    logit_bias = {"33281": -100, "30092": -100, "17293": -100, "531": -100, "27541": -100, "19353": -100,
                  "6303": -100, "19745": -100, "8610": -100, "36": -100, "12203": -100, "12463": -100, "43824": -100,
                  "9393": -100, "50": -100, "4145": -100, "49": -100, "693": -100, "38706": -100, "3767": -100,
                  "56": -100, "26684": -100, "76354": -100, "59586": -100, "1861": -100, "1097": -100, "64330": -100,
                  "81": -100, "594": -100, "15699": -100, "12884": -100, "82": -100, "8281": -100, "1626": -100,
                  "10331": -100, "220": -100, "30943": -100, "3423": -100, "39519": -100, "1636": -100, "1894": -100,
                  "7015": -100, "2794": -100, "47339": -100, "65772": -100, "5996": -100, "50411": -100, "39020": -100,
                  "7285": -100, "45948": -100, "894": -100}
    output = config.llm.create_chat_completion(
        messages=[  # type: ignore
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": original_phrase_r},
        ],
        max_tokens=768,
        temperature=0.8,
        top_k=90,
        top_p=0.9,
        logit_bias=logit_bias,
        seed=-1
    )

    result = output["choices"][0]["message"]["content"].strip()
    return result


def process_entry():
    """Shared processing of a single intent-map entry."""
    start_time = time.time()
    original_phrase = "What colour is the sky?"
    reworded = reword_phrase(original_phrase)
    print(f"\033[92mFinal Output: {reworded}\033[0m")

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"Processing time: {elapsed:.2f} seconds")

    return reworded

process_entry()

"""
Cold Temperature
Discovery
Energy Shield
Environmental Status
Equipment Status
Extreme Temperature
Freighter Combat
Missile Launch
Freighter Escape
Missile Destroyed
Hot Temperature
Inventory
Life Support
Monetary Transaction
Navigation
Notification
Oxygen Level
Personal Combat
Personal Protection
Protection from Environment
Radiation Exposure
REFERENCE
Starship Combat
Starship Movement
Toxic Environment
Vehicle Readiness
Vehicle Status
Debugging
"""

"""
model
prompt
best_of


"""
