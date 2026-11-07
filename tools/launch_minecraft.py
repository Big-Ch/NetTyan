"""Launch the isolated course client. No saved account tokens are read."""
import argparse,hashlib,json,os,subprocess,uuid
from pathlib import Path
import minecraft_launcher_lib.command

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--world',help='Existing local test world directory name for Quick Play')
args=parser.parse_args()
report=json.loads((ROOT/'data/minecraft-install.json').read_text(encoding='utf-8'))
folder=Path(report['game_directory'])
name='KadrReporter'
identifier=bytearray(hashlib.md5(('OfflinePlayer:'+name).encode()).digest())
identifier[6]=(identifier[6]&0x0f)|0x30
identifier[8]=(identifier[8]&0x3f)|0x80
options={'username':name,'uuid':str(uuid.UUID(bytes=bytes(identifier))),'token':'0',
         'executablePath':report['java'],'gameDirectory':str(folder),
         # UnionClef formats then parses distances using Double.parseDouble.
         # Decimal commas otherwise break state reads with multiple players/beds.
         'jvmArguments':['-Xmx2G','-Xms512M','-Duser.language=en','-Duser.country=US'],'customResolution':True,
         'resolutionWidth':'1280','resolutionHeight':'720','launcherName':'PersonaLab-Kadr'}
if args.world:
    world=(folder/'saves'/args.world).resolve()
    if world.parent!=(folder/'saves').resolve() or not (world/'level.dat').exists():
        raise ValueError('Choose an existing world inside the isolated saves directory')
    options['quickPlaySingleplayer']=args.world
command=minecraft_launcher_lib.command.get_minecraft_command(report['version_id'],folder,options)
with (ROOT/'data/minecraft-client.log').open('wb') as log:
    process=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
(ROOT/'data/minecraft-process.json').write_text(json.dumps({'pid':process.pid,'nickname':name,'mode':'offline local client; no authenticated account token supplied'},indent=2),encoding='utf-8')
print('Minecraft client PID:',process.pid)
