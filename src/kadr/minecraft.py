"""Small adapter over the same UnionClef/Py4J bridge used by NetTyan."""
import math
import time
from py4j.java_gateway import JavaGateway, GatewayParameters
from py4j.java_collections import JavaMap, JavaList

WALKABLE_FLOOR = {'grass_block', 'dirt', 'stone', 'cobblestone', 'stone_bricks',
                  'smooth_stone', 'andesite', 'polished_andesite', 'deepslate_tiles',
                  'quartz_block', 'smooth_quartz', 'oak_planks', 'spruce_planks'}

def plain(value):
    if isinstance(value,JavaMap): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,JavaList): return [plain(v) for v in value]
    return value

def coordinates(raw):
    parts=str(raw).split(',')
    if len(parts)==6: # Russian Java locale uses commas as decimal separators.
        return [float(parts[i]+'.'+parts[i+1]) for i in (0,2,4)]
    if len(parts)==3: return [float(x) for x in parts]
    raise ValueError('Неизвестный формат координат')

class MinecraftBridge:
    def __init__(self):
        self.gateway=JavaGateway(gateway_parameters=GatewayParameters(address='127.0.0.1',port=25333,read_timeout=3))
        self.goal=None
        self.task=None

    def inventory(self):
        raw=plain(self.gateway.entry_point.getInventoryFull())
        counts={}
        for slot in raw.get('slots',[]):
            if not slot.get('empty',True):
                name=slot['item'].removeprefix('minecraft:')
                counts[name]=counts.get(name,0)+int(slot.get('count',0))
        return counts

    def status(self):
        try:
            result=plain(self.gateway.entry_point.getGameState())
            if result.get('inGame'):
                result['xyz']=coordinates(result['self']['pos'])
                screen=plain(self.gateway.entry_point.getOpenScreen())
                result['screen']={k:v for k,v in screen.items() if k in ('open','title','screen','error')}
                result['inventory']=self.inventory()
                result['busy']=bool(self.gateway.entry_point.hasActiveTask())
                if self.goal:
                    result['goal']=self.goal
                    target=[self.goal[0]+0.5,self.goal[1],self.goal[2]+0.5]
                    result['distance_to_goal']=round(math.dist(result['xyz'],target),2)
                    result['arrival_confirmed']=result['distance_to_goal']<=2.0
                if self.task:
                    result['task']=dict(self.task)
                    if self.task['kind']=='item':
                        count=result['inventory'].get(self.task['item'],0)
                        result['task']['current_count']=count
                        result['task']['completed']=count>=self.task['count']
                    else:
                        result['task']['completed']=result.get('arrival_confirmed',False)
            return result
        except Exception:
            return {'inGame':False,'error':'Нет связи с игровым клиентом UnionClef'}

    def walk(self,dx,dz):
        if type(dx) is not int or type(dz) is not int or not (-4<=dx<=4 and -4<=dz<=4):
            return {'accepted':False,'error':'Разрешено движение максимум на 4 блока по каждой оси'}
        status=self.status()
        if not status.get('inGame'): return {'accepted':False,'error':'Сначала войдите в тестовый мир'}
        x,y,z=status['xyz']
        goal=[math.floor(x)+dx,math.floor(y),math.floor(z)+dz]
        try:
            self.gateway.entry_point.RunInnerCommand('@goto '+' '.join(str(v) for v in goal))
            self.goal=goal
            self.task={'kind':'walk','goal':goal,'started':time.monotonic()}
            return {'accepted':True,'arrival_confirmed':False,'goal':goal,'instruction':'Команда @goto поставлена в очередь. Прибытие проверяется отдельным inspect_minecraft.'}
        except Exception:
            return {'accepted':False,'error':'Игровой контроллер не принял движение'}

    def obtain(self,item,count):
        allowed={'oak_log','birch_log','spruce_log','oak_planks','stick','crafting_table','wooden_pickaxe','cobblestone','stone_pickaxe','torch'}
        if item not in allowed or type(count) is not int or not 1<=count<=8:
            return {'accepted':False,'error':'Недоступная задача или количество; разрешено 1–8 предметов из списка'}
        status=self.status()
        if not status.get('inGame'):
            return {'accepted':False,'error':'Нет игрового мира'}
        if status.get('screen',{}).get('open'):
            return {'accepted':False,'error':'Закройте игровое меню'}
        self.gateway.entry_point.RunInnerCommand(f'@get {item} {count}')
        self.goal=None
        self.task={'kind':'item','item':item,'count':count,'before':status['inventory'].get(item,0),'started':time.monotonic()}
        return {'accepted':True,'completed':False,'task':dict(self.task),'instruction':'Это поручение штатному AltoClef, не выдача предметов. Успех подтверждается настоящим инвентарём.'}

    def move_toward(self,state,target,*,run):
        """Move on a checked corridor without modifying the world."""
        if state.get('busy') or state.get('screen',{}).get('open') or not state.get('self',{}).get('onGround'):
            return False
        x,y,z=state['xyz']
        target_x,target_y,target_z=target
        distance=math.hypot(target_x-x,target_z-z)
        if abs(target_y-y)>0.5 or distance<2.5:
            return False
        dx,dz=(target_x-x)/distance,(target_z-z)/distance
        entry=self.gateway.entry_point
        # Check the forward corridor including player width and braking distance.
        steps=range(10 if run else 6)
        cells={(math.floor(x+dx*step/2-dz*side),math.floor(z+dz*step/2+dx*side))
               for step in steps for side in (-0.38,0,0.38)}
        floor_y=math.floor(y)
        for bx,bz in cells:
            floor=entry.getBlockAt(bx,floor_y-1,bz).get('id')
            if not floor or floor.removeprefix('minecraft:') not in WALKABLE_FLOOR:
                return False
            if any(entry.getBlockAt(bx,level,bz).get('is_air')!='true' for level in (floor_y,floor_y+1)):
                return False
        if not entry.lookAt(float(target_x),float(y+1.62),float(target_z)):
            return False
        if run:
            entry.holdKey('sprint',600)
        return bool(entry.holdKey('forward',520 if run else 320))

    def screenshot(self):
        return bytes(self.gateway.entry_point.getScreenshot())

    def voice_connected(self):
        try:
            entry=self.gateway.entry_point
            return (self.gateway.jvm.java.lang.System.getProperty('kadr.voice.pcm') is not None
                    and bool(entry.isVoiceChatConnected()))
        except Exception:
            return False

    def recent_chat(self):
        return list(self.gateway.entry_point.getRecentChat(30))

    def say(self,message):
        # Caller explicitly enables replies for the current server in the UI.
        message=' '.join(str(message).split())[:220]
        if not message:return {'queued':False}
        self.gateway.entry_point.ChatMessage('[Тайлер, ИИ] '+message)
        return {'queued':True,'delivered_confirmed':False}

    def stop(self):
        try:
            result=plain(self.gateway.entry_point.stopPathing())
            self.goal=None
            self.task=None
            return result
        except Exception:
            return {'stopped':False,'reason':'Игровой клиент недоступен'}

MINECRAFT_TOOLS=[
    {'type':'function','function':{'name':'inspect_minecraft','description':'Прочитать настоящее состояние игры и проверить достижение цели.','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
    {'type':'function','function':{'name':'walk_nearby','description':'Пройти по явной просьбе оператора на небольшое число блоков. Возвращает принятие задачи, не доказательство прибытия.','parameters':{'type':'object','properties':{'dx':{'type':'integer','minimum':-4,'maximum':4},'dz':{'type':'integer','minimum':-4,'maximum':4}},'required':['dx','dz'],'additionalProperties':False}}},
    {'type':'function','function':{'name':'obtain_item','description':'Поручить штатному игровому боту добыть или скрафтить предмет в своём тестовом мире. Он сам идёт к ресурсам, добывает и крафтит. Возвращает запуск, не успех. Вызывать только по игровой задаче оператора.','parameters':{'type':'object','properties':{'item':{'type':'string','enum':['oak_log','birch_log','spruce_log','oak_planks','stick','crafting_table','wooden_pickaxe','cobblestone','stone_pickaxe','torch']},'count':{'type':'integer','minimum':1,'maximum':8}},'required':['item','count'],'additionalProperties':False}}},
]
