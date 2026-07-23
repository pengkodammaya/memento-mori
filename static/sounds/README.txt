NEKYIA — sound assets
=====================

The audio engine (static/sounds.js) expects these files in this directory.
Drop your downloaded sound files here, renamed to match. The app degrades
silently if any are missing — it just won't play that one cue.

  ambient-drone.mp3   Continuous ocean/wind bed — loops under everything
                      (~30s+ loopable, low and steady)
  wave-swell.mp3      Secondary swell layer — fades in at the Sea of Souls
  chime-fate.mp3      Soft bell — one per fate-card hover (short, <2s)
  bell-summon.mp3     Deeper resonant bell — tolls on each Descent summon
  whisper-rise.mp3    Short soft wind/wisp — as each soul card renders (<1s)
  bell-final.mp3      Resonant closing bell — at The Return (Book XXIII)

Source: BBC Sound Effects (https://sound-effects.bbcrewind.co.uk/)
Licence: BBC RemArc — confirm your usage rights before public deployment.

To regenerate triggers or change which file maps to which event, see the
VOLUME / LOOPS maps at the top of static/sounds.js.
