"""Read-only staged-file check. Prints paths and pass/fail, never credentials."""
import json,re,subprocess
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
key=dotenv_values(ROOT/'.env').get('OPENAI_API_KEY','').encode()
failures=[]
total=0
for name in filter(None,files):
    if name.startswith(('data/','downloads/','.minecraft-course/','cached_models/','.venv/')) or name=='.env':
        failures.append({'file':name,'reason':'private path'})
    content=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
    total+=len(content)
    if key and key in content:failures.append({'file':name,'reason':'exact API credential'})
    if name.endswith(('.py','.ps1','.md','.yml','.example','.html','.json','.toml','.java')):
        if re.search(rb'\bsk-[A-Za-z0-9_-]{25,}|\b[0-9]{8,}:[A-Za-z0-9_-]{30,}',content):
            failures.append({'file':name,'reason':'credential-like literal'})
report={'ok':not failures,'files':len([f for f in files if f]),'bytes':total,'failures':failures,
        'scope':'Staged changes only; local credential compared without printing it'}
(ROOT/'data/publication-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
