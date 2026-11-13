"""Download the public CC0-dataset Piper voice; no hosted inference."""
import hashlib,json,os,urllib.request
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
folder=ROOT/'cached_models/piper'; folder.mkdir(parents=True,exist_ok=True)
report={}
for name in ('ru_RU-denis-medium.onnx','ru_RU-denis-medium.onnx.json','MODEL_CARD'):
    target=folder/name
    if not target.exists():
        urllib.request.urlretrieve('https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/denis/medium/'+name,target)
    report[name]={'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    print(name,target.stat().st_size,flush=True)
(folder/'download-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
