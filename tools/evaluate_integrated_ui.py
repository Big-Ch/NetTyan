"""Exercise the running app's real game loop, frame feed and speech outputs."""
import json,shutil,time,uuid
from pathlib import Path
from gradio_client import Client
ROOT=Path(__file__).resolve().parents[1]
client=Client('http://127.0.0.1:22228',verbose=False)
identity=uuid.uuid4().hex
client.predict(identity,api_name='/start')
objective='Сделай одну деревянную кирку в своём мире выживания. Используй obtain_item wooden_pickaxe 1 и проверь настоящий инвентарь.'
started=time.time()
client.predict(identity,objective,True,api_name='/start_game')
samples=[]
while time.time()-started<150:
    result=client.predict(identity,api_name='/live')
    state,phase=result[1],result[2]
    samples.append({'seconds':round(time.time()-started,2),'state':state,'phase':phase})
    if result[0]:shutil.copyfile(result[0],ROOT/'data/integrated-ui-game.png')
    if 'подтверждена' in phase or 'прервана' in phase or 'не достигнут' in phase:
        break
    time.sleep(2)
if time.time()-started>=150:client.predict(identity,api_name='/stop')
report={'objective':objective,'scope':'API of running local UI; real local Minecraft; scripted operator','samples':samples}
(ROOT/'data/integrated-ui-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PHASE:',samples[-1]['phase'])
print('INVENTORY:',samples[-1]['state'].get('inventory'))
print('FRAME:',bool(result[0]))
