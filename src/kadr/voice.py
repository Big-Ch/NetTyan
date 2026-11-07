"""Local Windows speech, no cloud endpoint and no cloned voice assets."""
import os
import subprocess
import uuid
import time
import wave
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_PIPER = None
_PIPER_LOCK = threading.Lock()

def play_local(path):
    """Play emitted WAV on this computer, so speech works beside Minecraft."""
    if os.name!='nt':return False
    try:
        import winsound
        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        return True
    except RuntimeError:return False

def stop_local_voice():
    if os.name=='nt':
        import winsound
        winsound.PlaySound(None,0)

def synthesize(text, runtime=None):
    if os.getenv("KADR_TTS_BACKEND", "piper") == "piper":
        return synthesize_piper(text)
    if os.getenv("KADR_TTS_BACKEND") == "openai":
        return synthesize_openai(text, runtime)
    if os.name != "nt":
        raise RuntimeError("Локальная озвучка этой сборки поддерживает Windows")
    folder = ROOT / "data" / "speech"
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex
    source, output = folder / (name + ".txt"), folder / (name + ".wav")
    source.write_text(str(text)[:1800], encoding="utf-8")
    try:
        result = subprocess.run(["pwsh.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools" / "kadr_voice.ps1"), "-TextPath", str(source), "-OutputPath", str(output)], capture_output=True, timeout=40, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not output.exists() or output.stat().st_size < 100:
            raise RuntimeError("Не удалось создать локальную озвучку")
        return str(output)
    finally:
        source.unlink(missing_ok=True)


def synthesize_piper(text):
    global _PIPER
    from piper import PiperVoice
    folder = ROOT / "data" / "speech"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / (uuid.uuid4().hex + ".wav")
    with _PIPER_LOCK:
        if _PIPER is None:
            _PIPER = PiperVoice.load(str(ROOT / "cached_models" / "piper" / "ru_RU-denis-medium.onnx"))
        with wave.open(str(output), "wb") as wav:
            _PIPER.synthesize_wav(str(text)[:1800], wav)
    return str(output)


def synthesize_openai(text, runtime):
    if runtime is None:
        raise RuntimeError("Для облачной озвучки нужен учёт бюджета")
    from openai import OpenAI
    from sqlalchemy import text as sql
    folder = ROOT / "data" / "speech"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / (uuid.uuid4().hex + ".wav")
    usage_id = runtime.reserve_request(0.10)
    started = time.monotonic()
    try:
        client = OpenAI(timeout=35, max_retries=0)
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts", voice="onyx", input=str(text)[:900],
            instructions="Говори по-русски, спокойно и естественно, как доброжелательный ироничный репортёр. Без театрального пафоса. Не добавляй слова.",
            response_format="wav",
        ) as response:
            response.stream_to_file(output)
        with wave.open(str(output), "rb") as wav:
            # Streaming WAV may carry an unknown-length sentinel in its header.
            # Count received PCM bytes, then write a canonical seekable WAV.
            params = wav.getparams()
            pcm = wav.readframes(wav.getnframes())
            duration = len(pcm) / params.nchannels / params.sampwidth / params.framerate
        normalized = output.with_suffix(".normalized.wav")
        with wave.open(str(normalized), "wb") as wav:
            wav.setparams(params._replace(nframes=len(pcm)//params.nchannels//params.sampwidth))
            wav.writeframes(pcm)
        normalized.replace(output)
        with runtime.db.engine.begin() as connection:
            connection.execute(sql("UPDATE kadr_usage SET status='tts-estimate',cost=:cost,seconds=:seconds WHERE id=:id"), {"id":usage_id,"cost":duration*0.015/60,"seconds":time.monotonic()-started})
        return str(output)
    except Exception as error:
        with runtime.db.engine.begin() as connection:
            connection.execute(sql("UPDATE kadr_usage SET status='tts-unknown' WHERE id=:id"), {"id":usage_id})
        raise RuntimeError("Облачная озвучка недоступна: " + type(error).__name__) from None
