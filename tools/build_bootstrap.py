"""Compile a tiny Fabric shim using Eclipse's compiler from Maven Central."""
import hashlib,json,subprocess,urllib.request,zipfile
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
compiler=ROOT/'downloads/ecj-3.42.0.jar'
url='https://repo1.maven.org/maven2/org/eclipse/jdt/ecj/3.42.0/ecj-3.42.0.jar'
if not compiler.exists():urllib.request.urlretrieve(url,compiler)
expected=urllib.request.urlopen(url+'.sha1',timeout=20).read().decode().strip()
if hashlib.sha1(compiler.read_bytes()).hexdigest()!=expected:raise RuntimeError('Compiler checksum mismatch')
report=json.loads((ROOT/'data/minecraft-install.json').read_text(encoding='utf-8'))
source=ROOT/'mods/kadr-bootstrap/src/KadrBootstrap.java'
classes=ROOT/'data/bootstrap-classes';classes.mkdir(exist_ok=True)
loader=ROOT/'.minecraft-course/libraries/net/fabricmc/fabric-loader/0.20.1/fabric-loader-0.20.1.jar'
subprocess.run([report['java'],'-jar',str(compiler),'-21','-cp',str(loader),'-d',str(classes),str(source)],check=True)
target=ROOT/'.minecraft-course/mods/kadr-bootstrap-1.0.jar'
manifest={'schemaVersion':1,'id':'kadr_bootstrap','version':'1.0','name':'Kadr Quick Play bootstrap',
          'environment':'client','entrypoints':{'main':['KadrBootstrap']},'depends':{'fabricloader':'>=0.20.1','altoclef':'*'}}
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('fabric.mod.json',json.dumps(manifest))
    archive.write(classes/'KadrBootstrap.class','KadrBootstrap.class')
print('Built:',target.name)
