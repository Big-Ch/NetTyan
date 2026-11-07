"""Build an editable replay from actual saved model replies; no API calls."""
import html
import json
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from kadr.voice import synthesize_piper

out = ROOT / 'demo'
assets = out / 'assets'
scenes = out / 'compositions'
assets.mkdir(exist_ok=True)
scenes.mkdir(exist_ok=True)
shutil.copyfile('C:/Windows/Fonts/arial.ttf', assets / 'Arial.ttf')
shutil.copyfile(ROOT.parents[1] / '.local/video-starter/node_modules/gsap/dist/gsap.min.js', assets / 'gsap.min.js')
report = json.loads((ROOT / 'docs/course/synthetic-evaluation.json').read_text(encoding='utf-8'))
titles = {
    'character': 'Починил велосипед. Есть история.',
    'save_confirmed_fact': 'Заметка только с разрешения',
    'memory_after_process_restart': 'Новый процесс. Память осталась.',
    'unrelated_user': 'Другой собеседник. Другой контекст.',
}
entries = []
start = 0.0
for case in report['cases']:
    if case['name'] not in titles:
        continue
    answer = case['result']['answer']
    voice = Path(synthesize_piper(answer))
    name = case['name']
    shutil.copyfile(voice, assets / (name + '.wav'))
    with wave.open(str(voice), 'rb') as wav:
        seconds = wav.getnframes() / wav.getframerate()
    duration = round(max(8.0, seconds + 4.0), 3)
    entries.append({'id': name, 'start': start, 'duration': duration, 'voice_seconds': seconds,
                    'input': case['input'], 'answer': answer, 'title': titles[name]})
    start = round(start + duration, 3)

entries.append({'id':'limits','start':start,'duration':10.0,'title':'Что проверено. Что ещё предстоит.',
 'input':'NetTyan + GPT-6 Luna + SQLite + локальный Piper',
 'answer':'Работают ответы, заметки, восстановление и удаление памяти. Minecraft читает состояние мира. Движение и независимые отзывы пока не подтверждены.'})
duration = round(start + 10, 3)
hosts, audio = [], []
for entry in entries:
    name, start, length = entry['id'], entry['start'], entry['duration']
    receipt = 'save_note: saved = true' if name == 'save_confirmed_fact' else {
        'memory_after_process_restart':'Проверка выполнена отдельным Python-процессом',
        'unrelated_user':'Заметки другого тестового пользователя: пусто',
        'character':'Настоящий ответ API, 7 ноября 2026',
        'limits':'Код: github.com/Big-Ch/NetTyan',
    }[name]
    scene = '''<template><style>
@font-face{font-family:KadrArial;src:url('assets/Arial.ttf')}
*{box-sizing:border-box}#root{position:absolute;inset:0;background:#f7faf7;color:#14251b;font-family:KadrArial,sans-serif}
.content{position:absolute;left:192px;top:150px;width:1536px}
h1{font-size:68px;line-height:1.12;letter-spacing:-2px;margin:0 0 38px}
.question{font-size:36px;line-height:1.3;margin:0 0 35px;color:#42584a;max-width:1470px}
.cm-pop{transform-origin:left bottom;background:#ddfb62;padding:32px 42px;border-radius:22px}
.reply{font-size:47px;line-height:1.28;margin:0}
.receipt{font-size:29px;line-height:1.3;margin:25px 0 0;color:#42584a}
</style><div id="root" data-composition-id="NAME" data-width="1920" data-height="1080">
<div class="content" data-hold><h1>TITLE</h1><p class="question">INPUT</p>
<div id="reply" class="clip" data-start="2" data-duration="REMAIN" data-track-index="2"><div class="cm-pop"><p class="reply">ANSWER</p></div></div>
<p id="receipt" class="clip receipt" data-start="2" data-duration="REMAIN" data-track-index="3">RECEIPT</p>
</div></div><script>
const tl=gsap.timeline({paused:true});
// Reused measured arrival from registry chat-message, shortened to one reply.
tl.fromTo('.cm-pop',{scale:0.75,opacity:0.6},{scale:1,opacity:1,duration:0.12,ease:'power2.out'},2);
tl.set({}, {}, LENGTH);
window.__timelines['NAME']=tl;
</script></template>'''
    for key, value in {'NAME':name,'TITLE':html.escape(entry['title']),'INPUT':html.escape(entry['input']),
                       'ANSWER':html.escape(entry['answer']),'RECEIPT':html.escape(receipt),
                       'LENGTH':str(length),'REMAIN':str(round(length-2,3))}.items():
        scene = scene.replace(key,value)
    (scenes / (name + '.html')).write_text(scene, encoding='utf-8')
    hosts.append(f'<div id="{name}" class="clip" data-composition-id="{name}" data-composition-src="compositions/{name}.html" data-start="{start}" data-duration="{length}" data-width="1920" data-height="1080" data-track-index="1" data-track-kind="graphics"></div>')
    if 'voice_seconds' in entry:
        audio.append(f'<audio id="voice-{name}" class="clip" src="assets/{name}.wav" data-start="{start+2}" data-duration="{entry["voice_seconds"]}" data-track-index="4" data-volume="1"></audio>')

root = '''<!doctype html><html lang="ru"><head><meta charset="UTF-8">
<script src="assets/gsap.min.js"></script><style>
@font-face{font-family:KadrArial;src:url('assets/Arial.ttf')}
*{margin:0;padding:0;box-sizing:border-box}html,body{width:1920px;height:1080px;overflow:hidden;background:#f7faf7}
#root{position:relative;width:1920px;height:1080px}
.label{position:absolute;left:192px;top:72px;font:29px KadrArial,sans-serif;color:#42584a;z-index:20}
.footer{position:absolute;left:192px;bottom:70px;font:28px KadrArial,sans-serif;color:#42584a;z-index:20}
</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="DURATION" data-width="1920" data-height="1080" data-fps="30">
HOSTS
<div id="label" class="clip label" data-start="0" data-duration="DURATION" data-track-index="5">Кадр / Persona Lab / реальные ответы модели</div>
<div id="footer" class="clip footer" data-start="0" data-duration="DURATION" data-track-index="5">Монтаж сохранённого тестового диалога. Независимых участников в этой записи нет.</div>
AUDIO
</div><script>const tl=gsap.timeline({paused:true});tl.set({}, {}, DURATION);window.__timelines['main']=tl;</script></body></html>'''
root = root.replace('DURATION',str(duration)).replace('HOSTS','\n'.join(hosts)).replace('AUDIO','\n'.join(audio))
(out / 'index.html').write_text(root,encoding='utf-8')
(out / 'timeline.json').write_text(json.dumps({'duration':duration,'entries':entries},ensure_ascii=False,indent=2),encoding='utf-8')
(out / 'SPEC.md').write_text(f'''# Демонстрация Кадра
1920×1080, 30 fps, {duration} с. Источник: docs/course/synthetic-evaluation.json.
Один пример: ремонт велосипеда, разрешённая заметка, новый процесс, другой собеседник.
Светлый фон #f7faf7, текст #14251b, ответ #ddfb62 из интерфейса Кадра.
Arial 29/36/47/68 px. Ответ появляется через 2 с, движение 0.12 с, затем неподвижное чтение.
Реплики озвучены бесплатным локальным Piper/Denis; это монтаж, не запись экрана.
Музыка не добавлена: запись нужна для проверки речи и фактов.
Запрещены придуманные отзывы, обещание зачёта, имитация успешного игрового движения.
Проверить середины всех пяти сцен, звук, длительность, подпись тестового сценария.
''',encoding='utf-8')
(out / 'STORYLINES.md').write_text('''# Выбор сценария
Выбран: один велосипед. Факт проходит через диалог, запись, перезапуск и изоляцию.
Другой вариант: обзор исходного кода. Менее наглядно для первого знакомства.
Другой вариант: игровая прогулка. Отложена, движение ещё не подтверждено.
''',encoding='utf-8')
print(f'Built {len(entries)} scenes, {duration}s; only local Piper used.')
