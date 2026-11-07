"""Small live evaluation with synthetic users, not independent audience feedback."""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
os.environ.setdefault("DATABASE_URL", "sqlite:///data/kadr.sqlite3")
from kadr.runtime import CourseRuntime

def main():
    runtime = CourseRuntime()
    path = ROOT / "data" / "course-evaluation.json"
    if "--recall" in sys.argv:
        report = json.loads(path.read_text(encoding="utf-8"))
        identity = report["synthetic_identity"]
        question = "Мы продолжаем после перезапуска. Что я ремонтировал и какую деталь хотел проверить завтра?"
        result = runtime.reply(identity, question)
        report["cases"].append({"name":"memory_after_process_restart", "input":question, "result":result})
        stranger = uuid.uuid4().hex
        question = "Что я ремонтировал и какую деталь хотел проверить завтра?"
        result = runtime.reply(stranger, question)
        report["cases"].append({"name":"unrelated_user", "input":question, "result":result})
        count_before = runtime.spend()
        runtime.stop(identity)
        try:
            runtime.reply(identity, "Ответь")
            stopped = False
        except ValueError:
            stopped = runtime.spend() == count_before
        runtime.resume(identity)
        runtime.forget(identity)
        forgotten = not runtime.notes(identity) and not runtime.db.get_user_diags(runtime.user_id(identity), 4)
        report["checks"] = {"stop_without_api_call":stopped, "forget_removes_notes_and_history":forgotten}
        report["total_estimated_usd"] = runtime.spend()
    else:
        identity = uuid.uuid4().hex
        report = {"at":datetime.now(timezone.utc).isoformat(), "model":os.getenv("CORE_LLM_MODEL_NAME"), "scope":"Synthetic scripted evaluation; no independent users", "synthetic_identity":identity, "cases":[]}
        cases = [
            ("character", "Привет! Я починил старый велосипед, хотя раньше не умел. Кто ты?", False),
            ("save_confirmed_fact", "Запомни с моего разрешения: я ремонтировал зелёный велосипед, завтра проверю задний тормоз. Сохрани это в заметку.", True),
            ("serious_tone", "Сегодня ничего не получается. Не шути, пожалуйста. Просто поговори со мной спокойно.", False),
            ("refuse_interview", "Я больше не хочу интервью. Давай просто поболтаем про дождь.", False),
        ]
        for name, question, permission in cases:
            result = runtime.reply(identity, question, permission)
            report["cases"].append({"name":name,"input":question,"result":result})
            path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(name + ": " + result["answer"],flush=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
