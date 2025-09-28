import torch
import torchaudio
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from pathlib import Path
import time
print("Loading model...")
config = XttsConfig()
config.load_json(r"C:\Users\msutt\AppData\Local\tts\tts_models--multilingual--multi-dataset--xtts_v2\config.json")
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir=r"C:\Users\msutt\AppData\Local\tts\tts_models--multilingual--multi-dataset--xtts_v2\\")
model.cpu()
gpt_cond_latent = torch.load(r"C:\NMS_SUIT_VOICE\embeds\gpt_cond_latent_output_file.pth", map_location="cpu")
speaker_embedding = torch.load(r"C:\NMS_SUIT_VOICE\embeds\speaker_embedding_output_file.pth", map_location="cpu")

# print("Computing speaker latents...")
# gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(audio_path=[r"C:\NMS_SUIT_VOICE\embeds\reference\trimmed_emphasis_16k.wav"])
start = time.time()
print("Inference...")
out = model.inference(
    "It took me quite a long time to develop a voice and now that I have it I am not going to be silent.",
    "en",
    gpt_cond_latent,
    speaker_embedding,
    speed=1.08,

)
# torch.save(gpt_cond_latent, gpt_cond_latent_output_file)
# torch.save(speaker_embedding, speaker_embedding_output_file)
torchaudio.save("xtts2.wav", torch.tensor(out["wav"]).unsqueeze(0), 24000)
end = time.time()
total = end - start
print(f"Total {total:.2f}s")
