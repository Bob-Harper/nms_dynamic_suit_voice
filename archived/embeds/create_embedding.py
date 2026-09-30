import torch
from pathlib import Path
from TTS.tts.utils.speakers import SpeakerManager

# Paths
speaker_wav = r"C:\NMS_SUIT_VOICE\embeds\reference\trimmed_emphasis.wav"
output_file = Path(r"C:\NMS_SUIT_VOICE\embeds\speaker_embed.pth")

encoder_model_path = "https://github.com/coqui-ai/TTS/releases/download/speaker_encoder_model/model_se.pth.tar"
encoder_config_path = "https://github.com/coqui-ai/TTS/releases/download/speaker_encoder_model/config_se.json"

encoder_manager = SpeakerManager(
    encoder_model_path=encoder_model_path,
    encoder_config_path=encoder_config_path,
    use_cuda=False
)

# Compute embedding
embedding = encoder_manager.compute_embedding_from_clip(speaker_wav)

# Save as .pth file
torch.save(embedding, output_file)
print(f"Saved embedding to {output_file}")
