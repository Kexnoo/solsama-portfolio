import re

# List of words/phrases to censor from bot replies before they are spoken or displayed.
BLOCKED_WORDS = []


# ------------------------------
# Profanity sanitization
def sanitize_reply(reply: str) -> str:
    """Remove or replace banned words from the GPT reply."""
    for word in BLOCKED_WORDS:
        reply = reply.replace(word, "[censored]")
        reply = reply.replace(word.capitalize(), "[censored]")
    return reply


# Strips the speaker prefixes
def strip_speaker_prefixes(text: str) -> str:
    """Remove 'Sol:' or similar speaker prefixes anywhere in the text."""
    # remove 'Sol:', 'SOL:', 'Sol-sama:', etc. at line starts
    text = re.sub(r'(?im)^\s*(sol(?:-?sama)?[\s\-:]+)', '', text)
    # also remove inline 'Sol:' patterns that sometimes appear mid-sentence
    text = re.sub(r'(?i)\bsol(?:-?sama)?[\s\-:]+', '', text)
    return text.strip()
