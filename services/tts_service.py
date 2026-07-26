import discord
import json
import base64
import tempfile
import asyncio
import io
import websockets

from pydub import AudioSegment
from elevenlabs import ElevenLabs
from TTS.api import TTS

from core.playback import current_playback


USE_XTTS = False  # flip to True to use local XTTS instead of ElevenLabs
tts_model = None


class ElevenLabsTTSConnection:
    def __init__(self, voice_id, api_key, model_id="eleven_multilingual_v2"):
        self.voice_id = voice_id
        self.api_key = api_key
        self.model_id = model_id
        self.uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}"
        self.ws = None
        self.queue = asyncio.Queue()
        self.running = False

    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        bos_message = {
            "text": " ",
            "voice_settings": {
                "stability": 0.9,
                "similarity_boost": 0.92,
                "style": 0.35,
                "use_speaker_boost": True
            },
            "xi_api_key": self.api_key
        }
        await self.ws.send(json.dumps(bos_message))
        self.running = True
        asyncio.create_task(self._process_queue())

    async def send_text(self, text):
        result_future = asyncio.Future()
        await self.queue.put((text, result_future))
        return await result_future

    async def _process_queue(self):
        while self.running:
            text, future = await self.queue.get()
            try:
                await self.ws.send(json.dumps({"text": text, "try_trigger_generation": True}))
                await self.ws.send(json.dumps({"text": ""}))

                audio_chunks = []
                async for message in self.ws:
                    data = json.loads(message)
                    if "audio" in data:
                        chunk = base64.b64decode(data["audio"])
                        audio_chunks.append(chunk)
                    if data.get("isFinal"):
                        break
                future.set_result(b"".join(audio_chunks))
            except Exception as e:
                future.set_exception(e)
            self.queue.task_done()

    async def close(self):
        self.running = False
        if self.ws:
            await self.ws.close()


def init_tts(app_state):
    global tts_model
    if USE_XTTS and tts_model is None:
        print("Loading local XTTS-v2 model...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
    return ElevenLabsTTSConnection(app_state["VOICE_ID"], app_state["ELEVENLABS_API_KEY"])


def tts_generate_xtts(text: str, sol_voice_path: str) -> str:
    try:
        output_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        tts_model.tts_to_file(
            text=text,
            speaker_wav=sol_voice_path,
            language="en",
            file_path=output_path
        )
        return output_path
    except Exception as e:
        print(f"[XTTS] generation error: {e}")
        raise


async def elevenlabs_stream_tts(text: str, voice_id: str, api_key: str, on_chunk):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_turbo_v2"
    async with websockets.connect(uri) as ws:
        bos_message = {
            "text": " ",
            "voice_settings": {
                "stability": 0.9,
                "similarity_boost": 0.92,
                "style": 0.35,
                "use_speaker_boost": True
            },
            "xi_api_key": api_key
        }
        await ws.send(json.dumps(bos_message))
        await ws.send(json.dumps({"text": text, "try_trigger_generation": True}))
        await ws.send(json.dumps({"text": ""}))

        async for message in ws:
            data = json.loads(message)
            if "audio" in data:
                audio_chunk = base64.b64decode(data["audio"])
                await on_chunk(audio_chunk)
            if data.get("isFinal"):
                break


async def speak(text, vc, client_ll, voice_id):
    audio_bytes = client_ll.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128"
    )
    await play_audio(vc, audio_bytes)


def mp3_to_pcm_bytes(audio_bytes):
    audio = AudioSegment.from_file(io.BytesIO(b"".join(audio_bytes)), format="mp3")
    audio = audio.set_channels(1).set_frame_rate(48000).set_sample_width(2)
    return audio.raw_data


async def play_audio(vc: discord.VoiceClient, audio_bytes):
    global current_playback
    if current_playback.get("playing") and current_playback.get("vc"):
        print("[TTS Audio] Already speaking. New speech dropped.")
        return

    audio_data = b"".join(audio_bytes) if isinstance(audio_bytes, (list, tuple, type((x for x in [])))) else audio_bytes
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_data)
        temp_path = f.name

    source = discord.FFmpegPCMAudio(temp_path)
    current_playback.update({"playing": True, "source": source, "vc": vc})

    def after_play(error):
        current_playback.update({"playing": False, "source": None, "vc": None})
        if error:
            print(f"[Audio Error] {error}")

    vc.play(source, after=after_play)


async def play_audio_file(vc: discord.VoiceClient, file_path: str):
    global current_playback
    try:
        if current_playback["playing"] and current_playback["vc"]:
            try:
                current_playback["vc"].stop()
            except Exception:
                pass
            current_playback["playing"] = False

        source = discord.FFmpegPCMAudio(file_path)
        current_playback.update({"playing": True, "source": source, "vc": vc})

        def _after(error):
            current_playback.update({"playing": False, "source": None})
            if error:
                print(f"[Audio File Error] {error}")

        vc.play(source, after=_after)
    except Exception as e:
        print(f"[play_audio_file] error: {e}")
