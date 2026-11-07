"""Read-only local/API checks. Never print credentials or raw API errors."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from dotenv import dotenv_values, load_dotenv

load_dotenv(ROOT / ".env")
os.environ.setdefault("NETTYAN_CHARACTER_NAME", "Kadr")
os.environ.setdefault("DATABASE_URL", "sqlite:///data/kadr.sqlite3")
(ROOT / "data").mkdir(exist_ok=True)

def main():
    report = {"python": sys.version.split()[0]}
    values = dotenv_values(ROOT / ".env")
    key = values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    report["key_present"] = bool(key)
    report["key_well_formed"] = bool(key) and not any(c.isspace() for c in key) and "=" not in key
    report["configured_keys"] = sorted(values)
    from character.character_manager import CharacterManager
    character = CharacterManager.get_main_character()
    report["character"] = character.get_names().Default
    report["prompt_chars"] = len(character.read_character_prompt())
    from data_flow.database import StreamerDatabase
    database = StreamerDatabase()
    report["database"] = database.engine.dialect.name
    report["mood"] = database.get_mood()
    if "--api" in sys.argv and report["key_well_formed"]:
        import openai
        try:
            import httpx
            proxy = os.getenv("HTTPS_PROXY")
            if "--proxy" in sys.argv:
                proxy = sys.argv[sys.argv.index("--proxy") + 1]
            client = openai.OpenAI(api_key=key, timeout=20, max_retries=0,
                                  http_client=httpx.Client(proxy=proxy, timeout=20, trust_env=False))
            model = os.getenv("CORE_LLM_MODEL_NAME", "openai/gpt-6-luna").removeprefix("openai/")
            report["model_access"] = client.models.retrieve(model).id
        except openai.APIError as error:
            report["api_error"] = type(error).__name__
            report["http_status"] = getattr(error, "status_code", None)
            body = getattr(error, "body", {})
            if isinstance(body, dict):
                detail = body.get("error", body)
                if isinstance(detail, dict):
                    report["api_error_code"] = detail.get("code")
                    message = str(detail.get("message", ""))
                    report["api_error_message"] = message.replace(key, "[redacted]")[:300]
    (ROOT / "data" / "doctor.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
