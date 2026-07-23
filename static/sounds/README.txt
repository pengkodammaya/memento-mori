NEKYIA — sound assets
=====================

The audio engine (static/sounds.js) expects these files in this directory.
Drop your downloaded sound files here, renamed to match. The app degrades
silently if any are missing — it just won't play that one cue.

  ambient-drone.wav   Continuous ocean/wind bed — loops under everything
                      (~30s+ loopable, low and steady)
  wave-swell.wav      Secondary swell layer — fades in at the Sea of Souls
  chime-fate.wav      Soft bell — one per fate-card hover (short, <2s)
  bell-summon.wav     Deeper resonant bell — tolls on each Descent summon
  whisper-rise.wav    Short soft wind/wisp — as each soul card renders (<1s)
  bell-final.wav      Resonant closing bell — at The Return (Book XXIII)

Format: WAV (BBC downloads are mastered as WAV — drop them in as-is).
Source: BBC Sound Effects (https://sound-effects.bbcrewind.co.uk/)
Licence: BBC RemArc — confirm your usage rights before public deployment.

To switch formats, change SOUND_EXT at the top of static/sounds.js.

To regenerate triggers or change which file maps to which event, see the
VOLUME / LOOPS maps at the top of static/sounds.js.
