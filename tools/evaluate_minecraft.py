"""Live local-world verification; no messages are sent to other players."""
import json,os,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT/'src'))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from kadr.runtime import CourseRuntime
from kadr.minecraft import MinecraftBridge

r=CourseRuntime()
identity=uuid.uuid4().hex
before=r.minecraft.status() if r.minecraft else MinecraftBridge().status()
question='Посмотри настоящее состояние Minecraft и скажи, где ты сейчас и есть ли рядом другие игроки. Никуда не двигайся.'
result=r.reply(identity,question,game_enabled=True)
report={'scope':'Local creative test world; not independent audience feedback','before':before,'request':question,'result':result}
(ROOT/'data/minecraft-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
