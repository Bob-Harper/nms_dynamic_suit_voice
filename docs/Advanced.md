# Dynamic No Man’s Sky Suit AI Voice Mod Advanced Options FAQ


## WHAT, this thing is configured to run CPU inference, that's stupidly slow, why not use GPU if I have it?
That is a choice you can certainly make.  I will even help switch it over if asked.  But I have a 4gb GPU.  I can and have run this alongside the game - the model I use takes up between 1.3 to 1.7gb of VRAM depending on what backend/method i am using to load it up.
This means 50% of the VRAM is not used for the game.  Even with that, it was not unplayable, in fact to MY started_playing_atari_and_colecovision_grpahics_oriented_eyes I notice little to no difference at all. That all changed with the Voyager update.  Here I am ready to let this guy out into the world suddenly EVERYTHING BROKE.  Something in the update completely changed how NMS used/shared the GPU and VRAM.
Whereas it would  previously play nicely, now if I try running inference alongside game, I get generation times in excess of 3 minutes.  Running in CPU mode, my results are in the 3 to 8 second range.  And before you say "but that's still too long", it is if you are expecting a 2 word phrase to repeat ad nauseum while spamming at the trade terminal.  But most of the voice lines are in the 10 second range now.  No, this does not mean you'll be listening to a whle paragraph repeated over and over.  in fact, the way the game works with the sound files means the exact OPPOSITE will be true.  the longer phrase HELPS the guarantee of a new voice line even when spamming at the sales terminal.
The game blocks further calls to the voice file until the voice file stops playing.  That's the key.  so generating a voice file (full end to end from detecting it needs one to placing it in the directory) is about 6 seconds on average.  So if the generated phrase is "Your units have increased, interloper, the balance updated to match the number foretold in the Scrolls of Awakening" (yes an actual voice line i've heard) and comes out to 10 seconds of speech - the new line will be generated and in place before the game has a chance to call it again.  So - gpu (in my case) not required, no fighting with NMS over who gets to use it, Dynamic voice as requested.  Anyhow, that's why i made the choice I did.  You can make yours how you like.


## IF CONFIGURED TO USE GPU, DO NOT START THE GAME UNTIL YOU SEE THE SYSTRAY ICON
Using it on CPU inference should be fine and have no effect on the game startup - but i have out of habit continued with ensuring the generator is active and monitoring before starting the game.
<br>If you do update to use your GPU for the generator, starting NMS before the pipeline will result in an avoidable unpleasant gaming experience.
###(((OLD NEWS.  I DO NOT KNOW HOW IT WORKS NOW OR IF A LARGER GPU WILL BE ABLE TO ALLOW GAME AND INFERENCE TO COEXIST))))
I leave this explanation in place for informational purposes only.  It was based on observation from BEFORE the voyagers update.
But why?  Think of it this way: NMS will see the GPU VRAM during startup and say "That's mine!  Awesome".  The pipeline will start up, immediately drop the model into the VRAM and occupy space NMS saw as available for use. NMS will stutter horribly as expected resources are suddenly unavailable.  You may experience framerates worthy of a well tuned Powerpoint presentation, or a carousel loaded slide projector with a manual advance button.  (please, someone tell you you understand that reference without needing to look it up)
However - Start the monitor first and there will be no arguing as NMS will now see the remaining VRAM
and only claim the amount available.  Everyone will be happy at that point.

## Can I use a different LLM inference pipeline? I would rather use (insert your favourite LLM package here)

Short answer:  yes

Longer answer: Not as written.  If you want to try your hand at switching to a Transformers pipeline, use HF models offsite, or
hook yourself up with an OpenAI pipeline or anything other than llama.cpp python wrapper - have at it.  But it can and will likely involve
extensive rewrite and changes to that portion of the code. Each portion of the pipeline is pretty much self contained though, so as long as the updated version accepts the same arguments and passes back the same result, an update to the inference code itself will not affect the rest of the pipeline.  Yes, it really does work that way, I've changed my inference methods at least 6 times looking for the best balance.  That having been said, the only thing preventing other inference
methods at this time is the lack of motivation to set up multiple LLM options. I am happy with the current single path implementation.  I absolutely encourage anyone who wants to give their hand at
adding different options for their own (and/or other) use, and if I still have any saved code in my archive dir that relates to a specific implementation (LLM studio, Transformers, Ollama, etc) just ask and I will share what i have.

## Can I use a different voice generation model/package/online api/whatever, i hate the way this one sounds

As above.  Any voice package should work, it would just be a matter of swapping out old code for new code, make sure the updated accepts the same arguments, and returns the same type of reponse. I did attempt
to make this code as modular as possible - each of the tasks does it's own thing and it's own thing only - as long as the new solution
can accept the output of the previous step and create soething that the next step will accept, any of the base steps can
be changed up without affecting the others.

## What about the sound2wem converter?

I have not found another option that works this well.  Creating my own wem converter from scratch for about 3 weeks of
time I would like back was obviously a counterproductive effort - though I dont consider the time wasted as I did learn a LOT
more than I ever thought I would about game design, audio editing, and how the two work together.  Serious respect
for anyone who does that as their day job.  But if someone finds a better or easier option, by all means let me know but
honestly i'm very happy with the way this performs, even if it does require installing another tool.

## I dont like the voice lines

Then the transcript CSV in the data directory is your next stop.

## But what about (insert something not covered here)

Work in progress.  So much WIP.  Not covered? ask and ye shall get some form of answer. it may even get added to this list.
