"""Bounded opt-in server demo: real timestamped frames, chat and local speech.

Start only after the operator has completed server authentication. Does not
register, log in, solve challenges, navigate, mine or publish anything.
"""
import argparse,json,os,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT/'src'))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from kadr.runtime import CourseRuntime
from kadr.session import GameSession
from kadr.game_chat import GameChat

parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=int,default=300)
parser.add_argument('--reply',action='store_true',help='Explicit permission for addressed game chat replies')
args=parser.parse_args()
if not 1<=args.seconds<=300:raise ValueError('Duration must be 1..300 seconds')
runtime=CourseRuntime();session=GameSession(runtime);bridge=session.bridge()
before=bridge.status()
if not before.get('inGame'):raise RuntimeError('Not in game')
server=str(bridge.gateway.entry_point.getServerInfoDict().get('server'))
if server!='mc.agicraft.ru':raise RuntimeError('Expected explicitly selected mc.agicraft.ru')
folder=ROOT/'data'/('community-'+time.strftime('%Y%m%d-%H%M%S'))
folder.mkdir(parents=True)
started=time.time();frames=[];last_state=0
chat=GameChat(session)
report={'started':started,'duration_requested':args.seconds,'server':server,'before':before,
        'folder':str(folder),'frames':frames,'method':'Actual game snapshots at measured timestamps; local Piper speech, not microphone or server voice chat.'}
(ROOT/'data/community-current.txt').write_text(str(folder),encoding='utf8')
try:
    if args.reply:chat.start(True,True)
    with (folder/'observations.jsonl').open('a',encoding='utf8') as log:
        while time.time()-started<args.seconds:
            at=time.time()-started
            try:
                image=bridge.screenshot()
                frame={'at':round(at,3),'file':f'frame-{len(frames):05d}.png'}
                (folder/frame['file']).write_bytes(image);frames.append(frame)
                if at-last_state>=2:
                    state=bridge.status();last_state=at
                    log.write(json.dumps({'at':at,'state':state,'chat':bridge.recent_chat()},ensure_ascii=False)+'\n');log.flush()
                    if not state.get('inGame') and not state.get('error'):
                        report['ended_reason']='Disconnected';break
            except Exception as error:
                log.write(json.dumps({'at':at,'error':type(error).__name__})+'\n');log.flush()
            time.sleep(0.35)
finally:
    chat.stop()
    report.update(duration_actual=time.time()-started,after=bridge.status(),chat_phase=chat.phase)
    (folder/'recording.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'folder':str(folder),'seconds':report['duration_actual'],'frames':len(frames)},ensure_ascii=False),flush=True)
