"""Install official Fabric API and require UnionClef's already bundled Tungsten."""
import hashlib,json,urllib.request,urllib.parse,zipfile
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
query=urllib.parse.urlencode({'game_versions':json.dumps(['1.21.11']),'loaders':json.dumps(['fabric'])})
with urllib.request.urlopen('https://api.modrinth.com/v2/project/fabric-api/version?'+query,timeout=30) as response:
    versions=json.load(response)
version=next(v for v in versions if v['version_type']=='release')
asset=next(f for f in version['files'] if f['primary'])
target=ROOT/'.minecraft-course/mods'/asset['filename']
urllib.request.urlretrieve(asset['url'],target)
if hashlib.sha512(target.read_bytes()).hexdigest()!=asset['hashes']['sha512']:
    raise RuntimeError('Fabric API checksum mismatch')
source=ROOT/'downloads/unionclef-1.21.11-0.95.66.jar'
target_mod=ROOT/'.minecraft-course/mods'/source.name
with zipfile.ZipFile(source) as src, zipfile.ZipFile(target_mod,'w',zipfile.ZIP_DEFLATED) as out:
    for item in src.infolist():
        value=src.read(item.filename)
        if item.filename=='fabric.mod.json':
            manifest=json.loads(value)
            manifest.setdefault('depends',{})['tungsten']='*'
            value=json.dumps(manifest,indent=2).encode()
        out.writestr(item,value)
report={'fabric_api_version':version['version_number'],'filename':asset['filename'],'sha512':asset['hashes']['sha512'],'unionclef_adjustment':'Declared dependency on bundled Tungsten; original downloaded JAR preserved','reason':'Tungsten was omitted by Fabric because its Fabric key-binding dependency was absent'}
(ROOT/'data/fabric-api-install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
