"""Real local-world task with synchronized game frames and emitted speech."""
import json,os,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT/'src'))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from kadr.runtime import CourseRuntime
from kadr.session import GameSession
runtime=CourseRuntime()
session=GameSession(runtime)
identity=uuid.uuid4().hex
folder=ROOT/'data/game-recording';folder.mkdir(exist_ok=True)
before=session.bridge().status()
started=time.time()
objective='Ты в своём тестовом мире выживания. Добудь дерево и сделай один верстак. Выполни игровую задачу через obtain_item crafting_table 1. Не утверждай успех до появления верстака в инвентаре.'
session.start(identity,objective,voice=True)
frames=[]
while time.time()-started<150:
    at=time.time()-started
    try:
        path=folder/f'frame-{len(frames):05d}.png'
        path.write_bytes(session.bridge().screenshot())
        frames.append({'at':round(at,3),'file':path.name})
    except Exception:pass
    if not session.active and time.time()-started>5:break
    time.sleep(0.2)
after=session.bridge().status()
if session.active:session.stop(identity)
report={'scope':'Real disposable local survival world; scripted operator objective, no independent audience',
        'started':started,'objective':objective,'before':before,'after':after,'phase':session.phase,
        'latest':session.latest,'frames':frames}
(ROOT/'data/game-session-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PHASE:',session.phase)
print('BEFORE:',before.get('xyz'),before.get('inventory'))
print('AFTER:',after.get('xyz'),after.get('inventory'))
print('FRAMES:',len(frames))
print('REPLY:',session.latest['answer'] if session.latest else 'No reply')
