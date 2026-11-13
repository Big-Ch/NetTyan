"""Opt-in roleplay in Minecraft chat."""
import hashlib,hmac,math,re,threading,time
from pathlib import Path
from kadr.club_dialogue import ClubDialogue
from kadr.minecraft import coordinates

COMMUNITY_SERVER = 'mc.agicraft.ru'

ADDRESS = re.compile(r'\b(?:тайлер|tyler|дёрден|дерден|durden|кадр|kadr|kadrreporter)\b', re.I)
REFUSAL = re.compile(r'(?:(?:я )?(?:пас|не хочу(?: играть| участвовать| домашку)?|отказываюсь|не буду(?: играть| участвовать)?)|нет(?:[, ]+спасибо)?|отстань)[.! ]*', re.I)
HOMEWORK = re.compile(r'\b(?:домашк\w*|дай задание|давай задание)\b', re.I)
ACCEPT = re.compile(r'(?:да|давай|беру|согласен|согласна|попробую)[.! ]*', re.I)
OPERATOR_CHAT = {'тайлер, дай домашку', 'тайлер, пас'}

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

    def start(self,allow_replies,voice,offer_homework=False):
        if not allow_replies:raise ValueError('Включи разрешение ответов в текущем игровом чате')
        if self.worker and self.worker.is_alive():return 'Игровой чат уже включён.'
        if not self.session.bridge().status().get('inGame'):raise ValueError('Сначала войди в выбранный игровой мир')
        self.cancel.clear()
        self.worker=threading.Thread(target=self._run,args=(voice,offer_homework),daemon=True)
        self.worker.start()
        self.phase=('Подходит к игрокам и предлагает домашку.' if offer_homework
                    else 'Слушает игровой чат. Попробуй «Тайлер, дай домашку».')
        return self.phase

    def stop(self):
        self.cancel.set()
        from kadr.voice import stop_minecraft_voice
        stop_minecraft_voice()
        self.phase='Игровой чат остановлен.'

    def _speak_in_game(self,bridge,message):
        from kadr.voice import send_minecraft_voice
        from kadr.tyler_voice import synthesize_tyler
        if self.cancel.is_set() or not bridge.voice_connected():
            return False
        try:
            return send_minecraft_voice(synthesize_tyler(message),bridge,self.cancel)
        except (RuntimeError,OSError,ValueError):
            return False

    def start_default(self):
        threading.Thread(target=self._warm_voice,daemon=True).start()
        self.cancel.clear()
        self.phase='Ждёт входа на mc.agicraft.ru.'
        self.worker=threading.Thread(target=self._wait_for_community,args=(False,),daemon=True)
        self.worker.start()

    def _warm_voice(self):
        from kadr.tyler_voice import warm_voice
        try:
            warm_voice()
        except (RuntimeError,OSError,ValueError) as error:
            self.session.record('game_voice_warm_error',{'type':type(error).__name__})

    def _wait_for_community(self,voice):
        bridge=self.session.bridge()
        while not self.cancel.is_set():
            try:
                if self._on_community(bridge):
                    self.phase='Бегает по площадке и предлагает домашки.'
                    self.session.record('game_chat_autostart',{'server':COMMUNITY_SERVER})
                    self._run(voice,True,community_only=True)
            except Exception as error:
                self.session.record('game_chat_error',{'type':type(error).__name__})
            if not self.cancel.is_set():
                self.phase='Ждёт входа на mc.agicraft.ru.'
                self.cancel.wait(2)

    @staticmethod
    def _on_community(bridge):
        state=bridge.status()
        if not state.get('inGame') or state.get('self',{}).get('dimension')!='OVERWORLD':
            return False
        entry=bridge.gateway.entry_point
        return entry.getUsername()=='KadrReporter' and entry.getServerInfoDict().get('server')==COMMUNITY_SERVER

    def _approach(self,bridge,name):
        for _ in range(8):
            if self.cancel.is_set() or self.session.active:
                return None
            state=bridge.status()
            if not state.get('inGame') or state.get('busy') or state.get('screen',{}).get('open'):
                return None
            target=next((player for player in state.get('players',[]) if player['name']==name),None)
            if target is None:
                return None
            distance=float(target['distance'].replace(',','.'))
            target_xyz=coordinates(target['pos'])
            if abs(target_xyz[1]-state['xyz'][1])>0.5:
                return None
            if distance<=4:
                bridge.gateway.entry_point.lookAtPlayer(name)
                return state['xyz'],distance
            if distance>12 or not bridge.move_toward(state,target_xyz,run=distance>6) or self.cancel.wait(0.65):
                return None
        return None

    def _patrol(self,bridge,state,anchor,direction):
        if not state.get('xyz') or state.get('busy') or state.get('screen',{}).get('open'):
            return
        x,y,z=state['xyz']
        angle=direction*math.pi/4
        target=(x+5*math.cos(angle),y,z+5*math.sin(angle))
        if math.dist(target,anchor)>9:
            target=(anchor[0],y,anchor[2])
        if bridge.move_toward(state,target,run=True):
            self.session.record('game_chat_patrol',{'from':state['xyz'],'toward':target})

    def _run(self,voice,offer_homework=False,*,community_only=False):
        bridge=self.session.bridge()
        previous=bridge.recent_chat()
        last=0
        last_invitation=time.monotonic()-90
        contacted=set()
        declined=set()
        invited_until={}
        attempted=set()
        invitations=0
        club=ClubDialogue()
        anchor=None
        next_patrol=0
        direction=0
        while not self.cancel.wait(1):
            try:
                if community_only and not self._on_community(bridge):
                    return
                current=bridge.recent_chat()
                overlap=0
                for length in range(min(len(previous),len(current)),0,-1):
                    if previous[-length:]==current[:length]:overlap=length;break
                incoming=current[overlap:]
                previous=current
                for line in dict.fromkeys(incoming):
                    parsed=player_message(line)
                    if not parsed:continue
                    nickname,message=parsed
                    player=nickname.casefold()
                    # Explicit requests typed in the bot client work for demos;
                    # never interpret the character's own tagged replies.
                    if player=='kadrreporter' and message.strip().casefold() not in OPERATOR_CHAT:continue
                    addressed=ADDRESS.search(message)
                    request=ADDRESS.sub('',message,count=1).strip(' ,:!–—') if addressed else message.strip()
                    refusal=REFUSAL.fullmatch(request)
                    invited=time.monotonic()<invited_until.get(player,0)
                    accepted=invited and ACCEPT.fullmatch(request)
                    if not addressed and not (invited and (refusal or accepted)):continue
                    contacted.add(player)
                    identity=self.identity(nickname)
                    if re.search(r'\b(?:стоп|остановись|stop)\b',message,re.I):
                        self.session.stop(self.session.identity or identity)
                        self.stop();return
                    if refusal and player in declined:continue
                    if not (refusal or accepted) and time.monotonic()-last<5:continue
                    self.session.record('game_chat_incoming',{'player':nickname,'message':message})
                    audio=None
                    played=False
                    if refusal:
                        invited_until.pop(player,None)
                        declined.add(player)
                        answer=club.farewell()
                    elif accepted:
                        invited_until.pop(player,None)
                        answer=club.acceptance()
                    elif re.search(r'забудь меня|удали (?:мои )?(?:заметки|историю)',message,re.I):
                        answer=self.session.runtime.forget(identity)
                    elif HOMEWORK.search(message):
                        declined.discard(player)
                        answer=club.homework()
                    else:
                        allowed=bool(re.search(r'\bзапомни\b',message,re.I))
                        # Visitors can talk and inspect; only operator UI starts physical tasks.
                        result=self.session.runtime.reply(identity,f'Игрок {nickname}: {message}',allowed,True,allow_actions=False)
                        if self.cancel.is_set():return
                        answer=result['answer']
                    if voice:
                        from kadr.voice import synthesize,play_local
                        try:
                            audio=synthesize(answer,self.session.runtime)
                        except RuntimeError:
                            self.session.record('game_chat_voice_error',{'player':nickname})
                        if self.cancel.is_set():return
                        if audio:
                            played=play_local(audio)
                    if self.cancel.is_set():return
                    # Voice has its own channel and need not wait for the chat rate limit.
                    if player=='kadrreporter' and (community_only or voice):
                        if self._speak_in_game(bridge,answer):
                            self.session.record('game_voice_queued',{'player':nickname})
                    # A request from this client consumes its own server chat cooldown.
                    if player=='kadrreporter' and self.cancel.wait(3.5):return
                    receipt=bridge.say(answer)
                    self.session.record('game_chat_reply',{'player':nickname,'answer':answer,'receipt':receipt,
                                                         'audio':audio,'playback_started':played})
                    last=time.monotonic()
                    if player!='kadrreporter' and (community_only or voice):
                        queued=self._speak_in_game(bridge,answer)
                        if queued:self.session.record('game_voice_queued',{'player':nickname})
                if offer_homework and not self.session.active:
                    state=bridge.status()
                    if not state.get('inGame') and not state.get('error'):
                        return
                    approached=False
                    can_invite=invitations<3 and time.monotonic()-max(last,last_invitation)>=90
                    for player in state.get('players',[]) if can_invite else ():
                        name=player['name']
                        if not re.fullmatch(r'[A-Za-z0-9_]{1,16}',name):continue
                        key=name.casefold()
                        if key=='kadrreporter' or key in contacted or key in attempted:continue
                        if float(player['distance'].replace(',','.'))>12:continue
                        if state.get('busy') or state.get('screen',{}).get('open'):break
                        if self.cancel.is_set():return
                        attempted.add(key)
                        approached=True
                        arrived=self._approach(bridge,name)
                        self.session.record('game_chat_approach',{'player':name,'start':state['xyz'],'arrival':arrived})
                        if arrived is None or self.cancel.is_set():break
                        invitation=club.invitation(name)
                        receipt=bridge.say(invitation)
                        self.session.record('game_chat_invitation',{'player':name,'text':invitation,'receipt':receipt})
                        contacted.add(key)
                        last_invitation=time.monotonic()
                        invited_until[key]=last_invitation+60
                        invitations+=1
                        if community_only or voice:
                            queued=self._speak_in_game(bridge,invitation.removeprefix(name+', '))
                            if queued:self.session.record('game_voice_queued',{'player':name})
                        break
                    if (community_only and not approached and not self.cancel.is_set()
                        and time.monotonic()>=next_patrol
                        and all(float(p['distance'].replace(',','.'))>6 for p in state.get('players',[]))):
                        position=state.get('xyz')
                        if position and (anchor is None or math.dist(anchor,position)>20):
                            anchor=position
                        if anchor:
                            self._patrol(bridge,state,anchor,direction)
                        direction=(direction+1)%8
                        next_patrol=time.monotonic()+1
            except Exception as error:
                self.phase='Игровой чат: '+type(error).__name__
                self.session.record('game_chat_error',{'type':type(error).__name__})
                if self.cancel.wait(5):return
