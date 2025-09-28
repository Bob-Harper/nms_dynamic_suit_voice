from TTS.api import TTS

# Get a list of available Coqui TTS models
available_models = TTS().list_models()

# Print the list of models
for model_name in available_models:
    print(model_name)
