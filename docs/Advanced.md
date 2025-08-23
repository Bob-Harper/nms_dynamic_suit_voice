# Dynamic No Man’s Sky Suit AI Voice Mod Advanced Options


## Can I use a different LLM inference pipeline? I would rather use (insert your favourite LLM package here)

Short answer:  yes

Longer answer: Not as written.  If you want to try your hand at switching to a Transformers pipeline, use HF models offsite, or
hook yourself up with an OpenAI pipeline or anything other than Ollama - have at it.  But it can and will likely involve
extensive rewrite and changes to that portion of the code.  That having been said, the only thing preventing other inference
methods at this time is the lack of motivation and expertise in setting up alternate LLM options.  I used to run LLM's
with customized python code but ever since I discovered Ollama I have left that world behind to focus on results and other
projects rather putting in time trying to reinvent the wheel.  I absolutely encourage anyone who wants to give their hand at
adding different options for their own (and/or other) use, but I fear I may not be of much help on specifics.

The basic concept of this pipeline remains unchagned however.

## Can I use a different voice generation model/package/online api/whatever, i hate the way this one sounds

As above.  Any voice package should work, it would just be a matter of swapping out old code for new code. I did attempt
to make this code as modular as possible - each of the tasks does it's own thing and it's own thing only - as long as the new solution
can accept the output of the previous step and create soething that the next step will accept, any of the base steps can
be changed up without affecting the others.

## What about the sound2wem converter?

I have not found another option that works this well.  Creating my own wem converter from scratch for about 3 weeks of
time I would like back was obviously a counterproductive effort - though I dont consider the time wasted as I did learn a LOT
more than I ever thought I would about game design, audio editing, and how the two work together.  Serious respect
for anyone who does that as their job.  But if someone finds a better or easier option, by all means let me know but
honestly i'm an very happy with the way this performs, even if it does require installing another entire github project.

## I dont like the voice lines

Then the transcript CSV in the data directory is your next stop.

## But what about (insert something not covered here)

Work in progress.  So much WIP.  ask and ye shall get some form of answer.

## Configuring Ollama

I find that the default timeout of Ollama being 5 minutes is too short - there are times where i could easily go longer than
that before i get another suit voice notification.  Ollama unloads the model when it reaches the timeout limit.  I set mine for 30.
 To do this, there are two options - adjust the code and add it to the parameters being sent, or editing the environment variables.
 In my case, I chose to edit the environment variables.

 From Ollama docs:
 Setting environment variables on Windows

On Windows, Ollama inherits your user and system environment variables.

    First Quit Ollama by clicking on it in the task bar.

    Start the Settings (Windows 11) or Control Panel (Windows 10) application and search for environment variables.

    Click on Edit environment variables for your account.

    Edit or create a new variable for your user account for OLLAMA_HOST, OLLAMA_MODELS, etc.

    Click OK/Apply to save.

    Start the Ollama application from the Windows Start menu.

Also from Ollama Docs:

If you're using the API, use the keep_alive parameter with the /api/generate and /api/chat endpoints to set the amount of time that a model stays in memory. The keep_alive parameter can be set to:

    a duration string (such as "10m" or "24h")
    a number in seconds (such as 3600)
    any negative number which will keep the model loaded in memory (e.g. -1 or "-1m")
    '0' which will unload the model immediately after generating a response

For example, to preload a model and leave it in memory use:

curl http://localhost:11434/api/generate -d '{"model": "llama3.2", "keep_alive": -1}'

To unload the model and free up memory use:

curl http://localhost:11434/api/generate -d '{"model": "llama3.2", "keep_alive": 0}'

Alternatively, you can change the amount of time all models are loaded into memory by setting the OLLAMA_KEEP_ALIVE environment variable when starting the Ollama server. The OLLAMA_KEEP_ALIVE variable uses the same parameter types as the keep_alive parameter types mentioned above. Refer to the section explaining how to configure the Ollama server to correctly set the environment variable.

The keep_alive API parameter with the /api/generate and /api/chat API endpoints will override the OLLAMA_KEEP_ALIVE setting.

The Ollama FAQS document has additional parameters that may be of interest when optimizing performans.and
