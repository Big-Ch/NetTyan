"""Launch from any working directory; credentials stay on the server."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
os.environ.setdefault("NETTYAN_CHARACTER_NAME", "Kadr")
os.environ.setdefault("DATABASE_URL", "sqlite:///data/kadr.sqlite3")
os.environ.setdefault("CORE_LLM_MODEL_NAME", "openai/gpt-6-luna")
os.environ.setdefault("CORE_LLM_MAX_TOKENS", "500")
os.environ.setdefault("LITELLM_LOG", "ERROR")
(ROOT / "data").mkdir(exist_ok=True)

if __name__ == "__main__":
    from kadr.app import main
    main()
