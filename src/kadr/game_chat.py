"""Opt-in incoming game chat routing; no unsolicited model calls or posts."""
import hashlib,hmac,re,threading,time
from pathlib import Path

def player_message(line):
    clean=re.sub('§.','',str(line))
    match=re.fullmatch(r'<([A-Za-z0-9_]{1,16})>\s*(.{1,1500})',clean)
    return match.groups() if match else None

class GameChat:
    def __init__(self,session):
        self.session=session
        self.cancel=threading.Event()
        self.worker=None
        self.phase='Игровой чат отключён.'
        secret=Path(__file__).resolve().parents[2]/'data/chat-identity-secret'
        if not secret.exists():
            import secrets
            secret.write_bytes(secrets.token_bytes(32))
        self.secret=secret.read_bytes()

    def identity(self,nickname):
        return hmac.new(self.secret,('minecraft:'+nickname.casefold()).encode(),hashlib.sha256).hexdigest()[:32]

    def start(self,allow_replies,voice):
        if not allow_replies:raise ValueError('Включи разрешение ответов в текущем игровом чате')
        if self.worker and self.worker.is_alive():return 'Игровой чат уже включён.'
        if not self.session.bridge().status().get('inGame'):raise ValueError('Сначала войди в выбранный игровой мир')
        self.cancel.clear()
        self.worker=threading.Thread(target=self._run,args=(voice,),daemon=True)
        self.worker.start()
        self.phase='Слушает игровой чат. Отвечает только на обращение «Кадр» или «Kadr».'
        return self.phase

    def stop(self):
        self.cancel.set()
        self.phase='Игровой чат остановлен.'

    def _run(self,voice):
        bridge=self.session.bridge()
        previous=bridge.recent_chat()
        last=0
        while not self.cancel.wait(1):
            try:
                current=bridge.recent_chat()
                overlap=0
                for length in range(min(len(previous),len(current)),0,-1):
                    if previous[-length:]==current[:length]:overlap=length;break
                incoming=current[overlap:]
                previous=current
                for line in incoming:
                    parsed=player_message(line)
                    if not parsed:continue
                    nickname,message=parsed
                    if nickname.casefold()=='kadrreporter' or not re.search(r'\b(?:кадр|kadr)\b',message,re.I):continue
                    identity=self.identity(nickname)
                    if re.search(r'\b(?:стоп|остановись|stop)\b',message,re.I):
                        self.session.stop(self.session.identity or identity)
                        self.stop();return
                    if time.monotonic()-last<5:continue
                    self.session.record('game_chat_incoming',{'player':nickname,'message':message})
                    audio=None
                    played=False
                    if re.search(r'забудь меня|удали (?:мои )?(?:заметки|историю)',message,re.I):
                        answer=self.session.runtime.forget(identity)
                    else:
                        allowed=bool(re.search(r'\bзапомни\b',message,re.I))
                        # Visitors can talk and inspect; only operator UI starts physical tasks.
                        result=self.session.runtime.reply(identity,f'Игрок {nickname}: {message}',allowed,True,allow_actions=False)
                        if self.cancel.is_set():return
                        answer=result['answer']
                        if voice:
                            from kadr.voice import synthesize,play_local
                            audio=synthesize(answer,self.session.runtime)
                            if self.cancel.is_set():return
                            played=play_local(audio)
                    if self.cancel.is_set():return
                    receipt=bridge.say(answer)
                    self.session.record('game_chat_reply',{'player':nickname,'answer':answer,'receipt':receipt,
                                                         'audio':audio,'playback_started':played})
                    last=time.monotonic()
            except Exception as error:
                self.phase='Игровой чат: '+type(error).__name__
                self.session.record('game_chat_error',{'type':type(error).__name__})
                if self.cancel.wait(5):return
