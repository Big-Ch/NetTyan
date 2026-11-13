"""Assemble actual game snapshots on their measured timestamps and emitted WAVs."""
import argparse,json,os,shutil,subprocess,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
parser=argparse.ArgumentParser()
parser.add_argument('--community',type=Path,help='Private folder from record_community_session.py')
args=parser.parse_args()
folder=args.community.resolve() if args.community else ROOT/'data/game-recording'
report=json.loads((folder/'recording.json' if args.community else ROOT/'data/game-session-evaluation.json').read_text(encoding='utf-8'))
events=[json.loads(line) for line in (ROOT/'data/game-session.jsonl').read_text(encoding='utf-8').splitlines()]
speech=[e for e in events if e['event'] in ('persona','game_chat_reply') and report['started']<=e['at']<=report['started']+report['frames'][-1]['at']+2]
files=sorted((ROOT/'data/speech').glob('*.wav'),key=lambda p:p.stat().st_mtime)
tracks=[]
for event in speech:
    payload=event['data']
    if event['event']=='game_chat_reply' and not payload.get('audio'):continue
    audio=Path(payload['audio']) if payload.get('audio') else min(files,key=lambda p:abs(p.stat().st_mtime-event['at']))
    if abs(audio.stat().st_mtime-event['at'])>4:raise ValueError('Speech provenance mismatch')
    with wave.open(str(audio),'rb') as wav:duration=wav.getnframes()/wav.getframerate()
    tracks.append({'file':str(audio),'start':round(event['at']-report['started'],3),'duration':duration,
                   'text':payload.get('result',payload)['answer']})
frames=report['frames']
if not frames:raise ValueError('No actual frames')
duration=report['duration_actual'] if args.community else max(frames[-1]['at']+2,max((t['start']+t['duration']+1 for t in tracks),default=0))
concat=[]
for index,frame in enumerate(frames):
    path=(folder/frame['file']).as_posix()
    end=frames[index+1]['at'] if index+1<len(frames) else duration
    concat += [f"file '{path}'",f"duration {max(0.01,end-frame['at']):.4f}"]
concat += [f"file '{(folder/frames[-1]['file']).as_posix()}'"]
concat_path=folder/'recording.ffconcat';concat_path.write_text('\n'.join(concat),encoding='utf-8')
label=folder/'video-label.txt';label.write_text('Кадр: mc.agicraft.ru, реальные кадры по времени; голос локальный Piper' if args.community else 'Кадр: реальная игровая сессия, выборка кадров по времени; локальный Piper',encoding='utf-8')
output=folder/'community-session.mp4' if args.community else ROOT/'docs/course/kadr-minecraft.mp4'
command=['ffmpeg','-hide_banner','-y','-f','concat','-safe','0','-i',str(concat_path)]
for track in tracks:command += ['-i',track['file']]
label_filter=label.relative_to(ROOT).as_posix()
filters=[f"[0:v]drawbox=x=0:y=0:w=iw:h=42:color=black@0.65:t=fill,drawtext=fontfile=demo/assets/Arial.ttf:textfile={label_filter}:fontcolor=white:fontsize=21:x=20:y=10[v]"]
for index,track in enumerate(tracks):
    ms=round(track['start']*1000)
    filters.append(f'[{index+1}:a]adelay={ms}:all=1[a{index}]')
if tracks:
    filters.append(''.join(f'[a{i}]' for i in range(len(tracks)))+f'amix=inputs={len(tracks)}:normalize=0,apad,loudnorm=I=-16:TP=-2:LRA=11[a]')
else:filters.append('anullsrc=r=24000:cl=mono[a]')
command += ['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(duration),'-r','30','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(output)]
with (folder/'video-render.log').open('w',encoding='utf-8') as log:subprocess.run(command,stdout=log,stderr=log,check=True)
manifest={'scope':report.get('scope','Actual selected community server, no independent reply guaranteed'),'duration':duration,'objective':report.get('objective','Five-minute peaceful gameplay and opt-in conversation'),
          'before':{'xyz':report['before']['xyz'],'inventory':report['before']['inventory']},
          'after':{'xyz':report['after']['xyz'],'inventory':report['after']['inventory']},
          'phase':report.get('phase',report.get('ended_reason','Recording finished')),'frames':len(frames),'speech':[{'start':t['start'],'duration':t['duration'],'text':t['text']} for t in tracks],
          'method':'Actual snapshots on measured timestamps; emitted local TTS mixed at readiness times. Last frame held for final speech. Not a microphone recording.'}
(folder/'video-evidence.json' if args.community else ROOT/'docs/course/game-evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Rendered actual game session:',duration,'seconds;',len(frames),'frames;',len(tracks),'speech clips')
