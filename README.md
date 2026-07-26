# solsama-portfolio (WIP)

DISCLAIMER: I AM STILL EDITING AND APPLYING FILES TO THIS REPO, THIS IS NOT ALL THE FILES

Public portfolio version of Sol, my AI Discord companion project (voice, memory, and Roblox dev agent systems).

## About this repo

This is a **sanitized, curated excerpt** of a larger private project (`solsama`). It exists to showcase architecture, coding style, and system design to recruiters and collaborators — it is **not** a complete or runnable clone of the private bot.

What's included:
- Selected `cogs/` (Discord command modules) demonstrating command handling and state tracking
- Selected `services/` modules demonstrating integration patterns with OpenAI, ElevenLabs TTS, and a screen-vision/OCR pipeline

What's intentionally excluded:
- All hardcoded credentials/tokens (real project uses environment variables; any example placeholders here are for illustration only and are not valid)
- Personal conversation logs, memory files, and other private/user data
- Audio samples and other binary assets
- Some internal modules not relevant to a portfolio review

## Notes on security

Any API keys or tokens referenced in this codebase are loaded from environment variables (e.g. `os.environ.get(...)`) at runtime and are never committed to source control. If you spot anything that looks like a real credential, please let me know — it would be a mistake, not an intentional disclosure.

## Tech stack

- Python, discord.py
- OpenAI GPT API
- ElevenLabs TTS / websockets streaming
- PIL, pytesseract for OCR-based screen vision
