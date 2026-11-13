"""Keep Chatterbox loaded in its own environment and return local WAV files."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import wave

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

# Keep third-party progress output off the JSON protocol.
protocol = sys.stdout
sys.stdout = sys.stderr

import numpy as np
import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


def reply(**result):
    print(json.dumps(result), file=protocol, flush=True)


def main():
    weights, reference = sys.argv[1:3]
    torch.set_num_threads(6)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    with patch("chatterbox.models.tokenizers.tokenizer.ChineseCangjieConverter", return_value=None):
        model = ChatterboxMultilingualTTS.from_local(weights, device)
    model.prepare_conditionals(reference, exaggeration=0.45)
    reply(ready=True, device=device)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            with patch("chatterbox.models.tokenizers.tokenizer.add_russian_stress", side_effect=lambda text: text):
                waveform = model.generate(request["text"], language_id="ru", exaggeration=0.45,
                                          cfg_weight=0.5, temperature=0.65)
            samples = waveform.detach().cpu().numpy().reshape(-1)
            if not len(samples) or not np.isfinite(samples).all() or np.max(np.abs(samples)) < 0.01:
                raise RuntimeError("Invalid audio")
            samples *= 0.85 / np.max(np.abs(samples))
            with wave.open(str(Path(request["output"])), "wb") as wav:
                wav.setparams((1, 2, model.sr, 0, "NONE", "not compressed"))
                wav.writeframes((samples * 32767).astype("<i2").tobytes())
            reply(ok=True)
        except Exception as error:
            reply(error=type(error).__name__)


if __name__ == "__main__":
    main()
