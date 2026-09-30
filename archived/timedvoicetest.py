import time
from TTS.api import TTS

print("Loading model...")
# tts = TTS("tts_models/en/jenny/jenny")
tts = TTS("tts_models/en/ljspeech/tacotron2-DDC_ph")

tts.to("cpu")
# tts.to("cuda")
print("Model ready.")

# preload check
print("Waiting 5 seconds to simulate idle preload...")
time.sleep(5)

# start timer
start = time.time()

tts.tts_to_file(
    text="Your decision making is suboptimal. Recalibrate your neural pathways to ensure continued existence.",
    file_path=r"C:\PythonScripts\NMS_SUIT_VOICE\speech.wav"
)

end = time.time()
print(f"Generation time after preload: {end - start:.2f} seconds")
print("Waiting 5 seconds to simulate idle before next generation...")
time.sleep(5)

# start timer
start = time.time()

tts.tts_to_file(
    text="Your decision making has improved. If you avoid taking further damage, your survival odds will increase.",
    file_path=r"C:\PythonScripts\NMS_SUIT_VOICE\speech2.wav"
)

end = time.time()
print(f"Generation time after second generation: {end - start:.2f} seconds")
