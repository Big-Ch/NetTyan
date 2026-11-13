"""Local, persistent Chatterbox process for Minecraft voice replies."""
import atexit
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import uuid

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data/tyler-voice-config.json"
LOCK = threading.Lock()
STRESS = {"космическая": "косми́ческая", "обезьяна": "обезья́на", "твоя": "твоя́",
          "домашка": "дома́шка", "домашку": "дома́шку", "собери": "собери́",
          "пяти": "пяти́", "блоков": "бло́ков", "бесполезное": "бесполе́зное",
          "изобретение": "изобрете́ние", "задание": "зада́ние", "своём": "своём",
          "построй": "постро́й", "табурет": "табуре́т",
          "назови": "назови́", "памятник": "па́мятник", "потом": "пото́м"}


class TylerVoice:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.responses = None

    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.process = None

    def _receive(self, timeout):
        try:
            result = self.responses.get(timeout=timeout)
            if result.get("error"):
                raise RuntimeError(result["error"])
            return result
        except (queue.Empty, RuntimeError):
            self.close()
            raise RuntimeError("Chatterbox voice worker unavailable") from None

    def start(self):
        if self.process is not None and self.process.poll() is None:
            return
        responses = queue.Queue()
        env = dict(os.environ, PYTHONUTF8="1", HF_HOME=self.config["hf_home"])
        with (ROOT / "data/tyler-voice-worker.log").open("ab") as log:
            process = subprocess.Popen(
                [self.config["python"], "-u", str(ROOT / "tools/tyler_voice_worker.py"),
                 self.config["weights"], self.config["reference"]],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                text=True, encoding="utf-8", env=env, cwd=ROOT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        self.process = process
        self.responses = responses

        def read():
            with process.stdout:
                for line in process.stdout:
                    try:
                        responses.put(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            responses.put({"error": "Voice worker exited"})

        threading.Thread(target=read, daemon=True).start()
        ready = self._receive(100)
        (ROOT / "data/tyler-voice-ready.json").write_text(
            json.dumps({**ready, "pid": process.pid, "parent_pid": os.getpid()}), encoding="utf-8"
        )

    def synthesize(self, text):
        cached = self.config.get("clips", {}).get(text)
        if cached and Path(cached).is_file():
            return cached
        self.start()
        prompt = re.sub(r"[а-яё]+", lambda m: _stress_word(m.group()), text[:250], flags=re.I)
        output = ROOT / "data/speech" / (uuid.uuid4().hex + ".wav")
        output.parent.mkdir(exist_ok=True)
        try:
            self.process.stdin.write(json.dumps({"text": prompt, "output": str(output)}) + "\n")
            self.process.stdin.flush()
        except OSError:
            self.close()
            raise RuntimeError("Voice worker disconnected") from None
        self._receive(90)
        return str(output)


def _stress_word(word):
    marked = STRESS.get(word.lower(), word)
    return marked.capitalize() if word[0].isupper() else marked


_worker = None


def worker():
    global _worker
    if _worker is None and CONFIG.exists():
        _worker = TylerVoice(json.loads(CONFIG.read_text(encoding="utf-8")))
        atexit.register(_worker.close)
    return _worker


def warm_voice():
    with LOCK:
        voice = worker()
        if voice:
            voice.start()


def synthesize_tyler(text):
    with LOCK:
        voice = worker()
        if voice:
            return voice.synthesize(text)
    from kadr.voice import synthesize_piper
    return synthesize_piper(text)
