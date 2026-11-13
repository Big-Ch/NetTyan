"""Prepare an isolated Fabric client, reusing public assets from installed Minecraft."""
import hashlib,json,os,shutil,sys,urllib.request
from pathlib import Path
from dotenv import load_dotenv
from minecraft_launcher_lib.install import install_minecraft_version

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
TARGET=ROOT/'.minecraft-course'
SOURCE=Path(os.environ['APPDATA'])/'.minecraft'
TARGET.mkdir(exist_ok=True)
(ROOT/'data').mkdir(exist_ok=True)
for name in ('assets','libraries'):
    source=SOURCE/name
    if source.exists() and not (TARGET/name).exists():
        print('Copying installed public assets:',name,flush=True)
        shutil.copytree(source,TARGET/name,dirs_exist_ok=True)
version='1.21.11'
if (SOURCE/'versions'/version).exists():
    shutil.copytree(SOURCE/'versions'/version,TARGET/'versions'/version,dirs_exist_ok=True)
install_minecraft_version(version,TARGET)
print('Installing official Fabric profile for',version,flush=True)
# Java's TLS provider is unavailable in this environment. Python downloads the
# official profile and Maven files with TLS validation and published SHA-256s.
loader='0.20.1'
with urllib.request.urlopen(f'https://meta.fabricmc.net/v2/versions/loader/{version}/{loader}/profile/json',timeout=30) as response:
    profile=json.load(response)
for library in profile['libraries']:
    group,artifact,revision=library['name'].split(':')
    relative=group.replace('.','/')+'/'+artifact+'/'+revision+'/'+artifact+'-'+revision+'.jar'
    target=TARGET/'libraries'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        urllib.request.urlretrieve(library['url']+relative,target)
    if library.get('sha256') and hashlib.sha256(target.read_bytes()).hexdigest()!=library['sha256']:
        raise RuntimeError('Fabric checksum mismatch: '+library['name'])
    print('Verified Fabric library:',library['name'],flush=True)
profile_folder=TARGET/'versions'/profile['id']
profile['jar']=version
profile_folder.mkdir(parents=True,exist_ok=True)
(profile_folder/(profile['id']+'.json')).write_text(json.dumps(profile,indent=2),encoding='utf-8')
java=next((TARGET/'runtime').rglob('java.exe'),None)
mods=TARGET/'mods';mods.mkdir(exist_ok=True)
jar=ROOT/'downloads'/'unionclef-1.21.11-0.95.66.jar'
jar.parent.mkdir(exist_ok=True)
if not jar.exists():
    urllib.request.urlretrieve('https://github.com/3ndetz/unionclef/releases/download/v0.95.66/'+jar.name,jar)
shutil.copy2(jar,mods/jar.name)
settings=TARGET/'options.txt'
if not settings.exists():
    settings.write_text('lang:ru_ru\nmaxFps:60\nrenderDistance:8\nsimulationDistance:5\nfullscreen:false\npauseOnLostFocus:false\n',encoding='utf-8')
report={'minecraft':version,'fabric_loader':loader,'version_id':profile['id'],'game_directory':str(TARGET),'mod':jar.name,'java':str(java)}
(ROOT/'data'/'minecraft-install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
