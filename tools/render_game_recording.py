"""Assemble actual game snapshots on their measured timestamps and emitted WAVs."""
import json,os,shutil,subprocess,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
report=json.loads((ROOT/'data/game-session-evaluation.json').read_text(encoding='utf-8'))
events=[json.loads(line) for line in (ROOT/'data/game-session.jsonl').read_text(encoding='utf-8').splitlines()]
speech=[e for e in events if e['event']=='persona' and report['started']<=e['at']<=report['started']+report['frames'][-1]['at']+2]
files=sorted((ROOT/'data/speech').glob('*.wav'),key=lambda p:p.stat().st_mtime)
tracks=[]
for event in speech:
    payload=event['data']
    audio=Path(payload['audio']) if payload.get('audio') else min(files,key=lambda p:abs(p.stat().st_mtime-event['at']))
    if abs(audio.stat().st_mtime-event['at'])>4:raise ValueError('Speech provenance mismatch')
    with wave.open(str(audio),'rb') as wav:duration=wav.getnframes()/wav.getframerate()
    tracks.append({'file':str(audio),'start':round(event['at']-report['started'],3),'duration':duration,
                   'text':payload.get('result',payload)['answer']})
frames=report['frames']
duration=max(frames[-1]['at']+2,max(t['start']+t['duration']+1 for t in tracks))
concat=[]
for index,frame in enumerate(frames):
    path=(ROOT/'data/game-recording'/frame['file']).as_posix()
    end=frames[index+1]['at'] if index+1<len(frames) else duration
    concat += [f"file '{path}'",f"duration {max(0.01,end-frame['at']):.4f}"]
concat += [f"file '{(ROOT/'data/game-recording'/frames[-1]['file']).as_posix()}'"]
(ROOT/'data/game-recording.ffconcat').write_text('\n'.join(concat),encoding='utf-8')
(ROOT/'data/game-video-label.txt').write_text('Кадр: реальная игровая сессия, выборка кадров по времени; локальный Piper',encoding='utf-8')
args=['ffmpeg','-hide_banner','-y','-f','concat','-safe','0','-i','data/game-recording.ffconcat']
for track in tracks:args += ['-i',track['file']]
filters=["[0:v]drawbox=x=0:y=0:w=iw:h=42:color=black@0.65:t=fill,drawtext=fontfile=demo/assets/Arial.ttf:textfile=data/game-video-label.txt:fontcolor=white:fontsize=21:x=20:y=10[v]"]
for index,track in enumerate(tracks):
    ms=round(track['start']*1000)
    filters.append(f'[{index+1}:a]adelay={ms}:all=1[a{index}]')
filters.append(''.join(f'[a{i}]' for i in range(len(tracks)))+f'amix=inputs={len(tracks)}:normalize=0,apad,loudnorm=I=-16:TP=-2:LRA=11[a]')
args += ['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(duration),'-r','30','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','docs/course/kadr-minecraft.mp4']
with (ROOT/'data/game-video-render.log').open('w',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=log,check=True)
manifest={'scope':report['scope'],'duration':duration,'objective':report['objective'],
          'before':{'xyz':report['before']['xyz'],'inventory':report['before']['inventory']},
          'after':{'xyz':report['after']['xyz'],'inventory':report['after']['inventory']},
          'phase':report['phase'],'frames':len(frames),'speech':[{'start':t['start'],'duration':t['duration'],'text':t['text']} for t in tracks],
          'method':'Actual snapshots on measured timestamps; emitted local TTS mixed at readiness times. Last frame held for final speech. Not a microphone recording.'}
(ROOT/'docs/course/game-evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Rendered actual game session:',duration,'seconds;',len(frames),'frames;',len(tracks),'speech clips')
