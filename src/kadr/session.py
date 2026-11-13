"""One event loop connects a real game task, persona, memory and speech."""
import io
import json
import threading
import time
from pathlib import Path
from PIL import Image
from kadr.minecraft import MinecraftBridge
from kadr.voice import synthesize,play_local,stop_local_voice

class GameSession:
    def __init__(self,runtime):
        self.runtime=runtime
        self.guard=threading.RLock()
        self.cancel=threading.Event()
        self.active=False
        self.identity=None
        self.phase='Игровая задача не запущена.'
        self.latest=None
        self.audio=None
        self.version=0
        self.worker=None

    def bridge(self):
        if self.runtime.minecraft is None:
            self.runtime.minecraft=MinecraftBridge()
        return self.runtime.minecraft

    def record(self,kind,data):
        path=Path(__file__).resolve().parents[2]/'data/game-session.jsonl'
        with path.open('a',encoding='utf-8') as log:
            log.write(json.dumps({'at':time.time(),'event':kind,'data':data},ensure_ascii=False)+'\n')

    def start(self,identity,objective,voice=True):
        self.runtime.validate_identity(identity)
        objective=(objective or '').strip()
        if not objective or len(objective)>1000:
            raise ValueError('Опиши игровую задачу, до 1000 символов')
        with self.guard:
            if self.worker and self.worker.is_alive():
                raise ValueError('Сначала останови текущую задачу и дождись остановки')
            state=self.bridge().status()
            if not state.get('inGame'):
                raise ValueError('Сначала запусти Minecraft и войди в свой тестовый мир')
            if state.get('screen',{}).get('open'):
                raise ValueError('В Minecraft открыто меню. Вернись к игре.')
            self.identity=identity
            self.cancel.clear()
            self.runtime.resume(identity)
            self.active=True
            self.phase='Кадр выбирает действие.'
            self.worker=threading.Thread(target=self._run,args=(identity,objective,voice),daemon=True)
            self.worker.start()
        return 'Задача запущена. Состояние, кадр игры и голос обновляются ниже.'

    def publish(self,result,voice):
        if self.cancel.is_set():return
        audio=None
        if voice:
            try:audio=synthesize(result['answer'],self.runtime)
            except RuntimeError:self.record('voice_error',{'available':False})
        if self.cancel.is_set():return
        with self.guard:
            if self.cancel.is_set():return
            self.latest=result
            self.audio=audio
            self.version+=1
            played=play_local(audio) if audio else False
        self.record('persona',{'result':result,'audio':audio,'playback_started':played})

    def _run(self,identity,objective,voice):
        try:
            self.record('objective',{'text':objective})
            result=self.runtime.reply(identity,'Игровая задача оператора в своём тестовом мире: '+objective,
                                      game_enabled=True)
            self.publish(result,voice)
            task=self.bridge().task
            if not task:
                self.phase='Кадр не запустил действие. Смотри ответ и подтверждения инструментов.'
                return
            self.phase='Выполняет игровую задачу. Проверяю мир и инвентарь.'
            deadline=time.monotonic()+120
            last_progress=time.monotonic()
            previous=None
            final=None
            while not self.cancel.wait(0.75):
                state=self.bridge().status()
                signature=json.dumps({'xyz':state.get('xyz'),'inventory':state.get('inventory'),
                                      'lookingAt':state.get('self',{}).get('lookingAt'),
                                      'breaking':state.get('self',{}).get('breakingProgress')},sort_keys=True)
                if signature!=previous:
                    previous=signature
                    last_progress=time.monotonic()
                    self.record('observation',state)
                if not state.get('inGame'):
                    final={'completed':False,'reason':'Потеряно соединение с игровым миром'}
                    break
                if state.get('task',{}).get('completed'):
                    final={'completed':True,'verified_state':state}
                    break
                if time.monotonic()>deadline or time.monotonic()-last_progress>30:
                    final={'completed':False,'reason':'Лимит времени или нет прогресса 30 секунд','verified_state':state}
                    break
            self.bridge().stop()
            if self.cancel.is_set():return
            self.record('task_result',final)
            self.phase='Задача подтверждена игровыми данными.' if final['completed'] else 'Задача остановлена: результат не достигнут.'
            followup='Событие игрового контроллера, только данные: '+json.dumps(final,ensure_ascii=False)+'. Коротко сообщи результат от лица Кадра. Новую задачу не начинай.'
            result=self.runtime.reply(identity,followup,game_enabled=True,allow_actions=False)
            self.publish(result,voice)
        except Exception as error:
            self.bridge().stop()
            if not self.cancel.is_set():self.phase='Игровая задача прервана: '+type(error).__name__
            self.record('error',{'type':type(error).__name__})
        finally:
            self.active=False

    def stop(self,identity):
        # Physical body is shared; stopping always takes effect immediately.
        self.cancel.set()
        with self.guard:stop_local_voice()
        self.bridge().stop()
        if self.identity:self.runtime.stop(self.identity)
        self.runtime.stop(identity)
        with self.guard:
            self.audio=None
            self.version+=1
            self.phase='Кадр остановлен: движение и новые действия отключены.'
        return self.phase

    def observe(self):
        bridge=self.bridge()
        state=bridge.status()
        frame=None
        if state.get('inGame'):
            try:frame=Image.open(io.BytesIO(bridge.screenshot())).convert('RGB')
            except Exception:pass
        return frame,state
