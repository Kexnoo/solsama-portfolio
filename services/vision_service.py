import os
import time
import base64
import hashlib
import datetime
import pyautogui
import openai
import pytesseract

from PIL import Image

from utils.text_utils import sanitize_reply
from services.openai_service import get_gpt_reply
from services.tts_service import play_audio


_last_image_hash = None
_last_vision_time = 0


def compress_image(fname: str, max_size=(640, 360)) -> str:
    """Downscale and convert screenshot to JPEG for cheaper uploads."""
    img = Image.open(fname)
    img.thumbnail(max_size)
    compressed_path = fname.replace(".png", "_small.jpg")
    img.save(compressed_path, "JPEG", quality=60, optimize=True)
    return compressed_path


def hash_image(fname: str) -> str:
    with open(fname, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def extract_text_summary(image_path: str) -> str:
    """Lightweight OCR text summary (no OpenAI tokens)."""
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
        text = text.strip()
        if len(text) < 20 or sum(c.isalpha() for c in text) / max(1, len(text)) < 0.4:
            return ""
        return text[:1000]
    except Exception as e:
        print(f"[OCR] {e}")
        return ""


async def capture_and_caption(
    user_prompt=None,
    *,
    awareness,
    bot,
    client_ll,
    voice_id,
    get_context_prompt_limit=50,
):
    """Take a screenshot, compress, and describe it efficiently."""
    global _last_image_hash, _last_vision_time
    try:
        os.makedirs("screenshots", exist_ok=True)
        fname = f"screenshots/sol_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        pyautogui.screenshot(fname)
        print("Captured Screen!")

        current_hash = hash_image(fname)
        if current_hash == _last_image_hash and time.time() - _last_vision_time < 30:
            print("[VISION] Skipping duplicate or recent screenshot.")
            return None
        _last_image_hash = current_hash
        _last_vision_time = time.time()

        compressed = compress_image(fname)
        ocr_text = extract_text_summary(compressed)

        vision_prompt = (
            user_prompt or
            "Describe what you see in this screenshot in one or two sentences. "
            "If it's programming, summarize what kind of code is shown. "
            "If it's a game, describe what seems to be happening."
        )
        if ocr_text:
            vision_prompt += f"\n\nSome text detected:\n{ocr_text[:500]}"

        with open(compressed, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Sol's visual cortex. Describe screenshots clearly and succinctly."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ],
                },
            ],
        )
        caption = response.choices[0].message.content
        msg = f"[SCREENSHOT]: {caption}"
        awareness.remember("Sol", msg, context="visual")

        try:
            personality_context = awareness.get_context_prompt(limit=get_context_prompt_limit)
            full_prompt = (
                f"Recent conversation and internal state:\n{personality_context}\n\n"
                f"Sol has just seen this: \"{caption}\".\n"
                "Respond naturally in her personality. "
                "Keep it to 1-2 sentences and don't repeat the description exactly."
            )
            reply = await get_gpt_reply(full_prompt, speaker="Sol")
            reply = sanitize_reply(reply)
            awareness.remember("Sol", reply, context="voice")

            for vc in bot.voice_clients:
                try:
                    audio_bytes = client_ll.text_to_speech.convert(
                        text=reply,
                        voice_id=voice_id,
                        model_id="eleven_turbo_v2",
                        output_format="mp3_44100_128",
                    )
                    await play_audio(vc, audio_bytes)
                except Exception as e:
                    print(f"[VisionSpeech] playback error: {e}")
        except Exception as e:
            print(f"[VisionSpeech] error interpreting screenshot: {e}")

        return caption
    except Exception as e:
        print(f"[capture_and_caption] error: {e}")
        return None


async def should_use_vision(user_text: str, user_name: str) -> tuple[bool, str]:
    """
    Determines if Sol should take a screenshot (vision mode).
    Only returns YES if the request came from the bot's designated owner/creator.
    """
    system_prompt = (
        f"You are Sol's (soul) internal decision logic.\n"
        f"If the user speaking is named '{user_name}', and that user is Sol's creator, "
        f"and they explicitly ask you to look at, see, check, read, or describe something on their screen, "
        f"respond with 'YES:' followed by what to look at (e.g., 'YES: look at the code', 'YES: read the screen').\n"
        f"If the message comes from anyone else, or if the message does not involve looking, respond 'NO'."
    )
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Message from {user_name}: {user_text}"}
        ],
        temperature=0.2,
        max_tokens=10
    )
    msg = response.choices[0].message.content.strip()
    if msg.upper().startswith("YES"):
        reason = msg.split(":", 1)[-1].strip()
        return True, reason
    return False, ""
