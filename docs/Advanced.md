# Dynamic No Man’s Sky Suit AI Voice Mod — Advanced Options FAQ

## WHAT, this thing is configured to run CPU inference, that's stupidly slow, why not use GPU if I have it?
That is a choice you can certainly make.

But I have a 4GB GPU. Testing will be difficult, if not impossible.

I can and have run this alongside the game—the LLM I use takes up between 1.3 to 1.7GB of VRAM depending on what backend or method I am using to load it up. That means nearly 50% of my VRAM is taken away from the game. Even with that, it was playable; in fact, to my started-playing-Atari-and-ColecoVision-graphics-oriented eyes, I noticed little to no difference at all.

That all changed with the Voyager update. Just as I was ready to let this guy out into the world, suddenly EVERYTHING BROKE. Something in that update completely changed how NMS used and shared the GPU and VRAM.

Whereas it would previously play nicely, running GPU inference alongside the game after Voyager pushed generation times in excess of 3 minutes. Running in CPU mode, my results are back down in the 3 to 8 second range. And before you say "but that's still too long", it only is if you are expecting a 2-word phrase to repeat ad nauseam while spamming at the trade terminal. Most of the generated voice lines are in the 10-second range now.

No, this does not mean you'll be listening to a whole paragraph repeated over and over. In fact, the way the game handles sound files means the exact OPPOSITE is true. A longer phrase actually *helps* guarantee a brand-new voice line even when spamming at a sales terminal.

The game blocks further calls to a voice file until the currently playing audio stops. That's the key. Full end-to-end generation (from detecting a trigger to placing the compiled `.wem` in the directory) takes about 6 seconds on my rig on average. Because the new Kokoro ONNX voice engine generates audio roughly 4x faster than the old Coqui setup—and we run a rolling look-ahead cache on frequently used lines—your fresh line is already waiting in the wings long before the game finishes speaking the current one.

If the generated phrase is *"Your units have increased, interloper, the balance updated to match the number foretold in the Scrolls of Awakening"* (yes, an actual voice line I've heard) and comes out to 10 seconds of speech, the replacement line is locked, loaded, and swapped into place before the game even has a chance to call it again. No GPU required, no fighting with NMS over VRAM, and a truly dynamic voice as promised. That's why I made the choice I did. You can make yours how you like.

## IF CONFIGURED TO USE GPU, DO NOT START THE GAME UNTIL ALL MODELS ARE LOADED.
Using CPU inference has zero effect on game startup, though I still make a habit of ensuring the generator is active and monitoring before launching NMS. (And yes, a one-click "Launch NMS" button right inside the DSV Manager is on the roadmap.)

If you *do* modify the config to use your GPU for inference, starting NMS before the pipeline finishes loading may result in an avoidable, unpleasant gaming experience.

### (((OLD NEWS. I DO NOT KNOW HOW IT WORKS NOW OR IF A LARGER GPU ALLOWS GAME AND INFERENCE TO COEXIST)))
[[begin reference section]]

<i>
I leave this explanation in place for informational and historical archive purposes only. It was based on observations from BEFORE the Voyager update.

Think of it this way: NMS will inspect your GPU VRAM during startup and say, "That's mine! Awesome." If you launch the pipeline afterward, it will immediately drop the models into VRAM and occupy space NMS already claimed as available. NMS will stutter horribly as expected resources suddenly vanish.

When I tested this, I experienced a variety of framerates ranging from the highest FPS of an absurdly well-tuned PowerPoint presentation all the way down to the approximate FPS of a carousel-loaded slide projector with a manual advance button.

However, if you start the monitor first, NMS sees the remaining VRAM on boot and only claims what is actually left. Everyone stays happy.
</i>

[[end reference section]]

If only it had stayed that way.  Alas, it did not, and here we are.

## Can I use a different OS?
Short answer: Likely. Maybe? NO IDEA!

Longer answer: All of my development and testing is on Windows 11. Python itself is portable, and the core generation logic ("swap out file, generate a new one, cache it for next time") is straightforward.

However, getting the watcher to reliably *detect* the exact microsecond the game accesses a `.wem` file in the mods folder is OS-specific. Standard file-access timestamps (`st_atime`) don't work reliably on modern drives, so this project uses native Windows Kernel Level-1 Oplocks (`CreateFileW` / `DeviceIoControl`) to catch the game opening the file. Porting that tripwire mechanism to Linux/Proton or macOS will require more knowledgeable heads than mine. Check the Discussions tab on the Nexus Mods page—there is already some conversation happening around this exact topic.

## Can I use a different LLM inference pipeline? I would rather use (insert your favourite LLM package here)
Short answer: Yes.

Longer answer: Other models will likely require changes to the prompting, as the current setup is specifically tuned for `Qwen3-4B-Q8_0`. Even other Qwen variants react differently. If you want to switch to a Hugging Face Transformers pipeline, use off-site APIs, or hook up Ollama/LM Studio instead of `llama-cpp-python`, have at it. Just expect to rewrite that specific module and re-tune your prompts.

Each portion of the pipeline is modular and self-contained. As long as your updated module accepts the same arguments and returns a clean string, changing the inference backend will not break the rest of the pipeline. I've swapped my own inference methods at least 6 times looking for the best balance.

Right now, I am sticking with a single local GGUF implementation to keep things simple, though multi-model management and per-model prompt profiles are on the roadmap. If anyone wants to add support for other backends, go for it—and if I still have old archive snippets for Ollama, LM Studio, or Transformers lying around, just ask and I'll share what I have.

## Can I use a different voice generation model/package/online API/whatever? I hate the way this one sounds.
First, check the **Audio Modifiers** and **Models** tabs inside the DSV Manager! The mod now uses **Kokoro-82M (ONNX)**, which boots into memory in under 2 seconds and comes with 28 distinct built-in English voice identities (`am_adam`, `af_bella`, `bf_emma`, etc.) plus decoupled real-time DSP sliders for pitch, pacing, throat size (formants), and robotic ring modulation. You can dial in anything from a clinical ship computer to a paranoid, angry space drill sergeant without downloading anything external.

If you *still* want to rip it out and use a completely different TTS package or online API, the same modularity rule applies: swap out the generation step in `tts_utils.py`, accept the text string, and output a valid 44.1kHz `.wav` file for the converter to pick up.

## What about the `.wem` converter?
We now use a standalone conversion tool that works without requiring Audiokinetic Wwise or massive project directories. I forked `wav2wem` and decoupled the extra executables that were bundled inside for transparency and to eliminate false-positive antivirus flags. If someone finds an even faster or cleaner CLI converter, please let me know—for now, `wav2wem` is the best solution.

## I don't like the voice lines.
You can inspect and edit the base transcriptions, categories, and intents inside `data/nms_suit_voice_transcripts.json` (and tweak the personality/wordiness modifiers in `data/prompt_data.json`). Exposing a full live Prompt Workbench directly inside the DSV Manager UI is also high on the roadmap.

## But what about (insert something not covered here)?
Work in progress. So much WIP. Not covered? Ask, and you'll get some form of answer. It might get added to this FAQ, thrown onto the roadmap, or met with a polite *"that's neat, but..."* Who knows.
