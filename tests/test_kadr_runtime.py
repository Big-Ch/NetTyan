"""Offline integration checks using the real NetTyan database and fake model."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
temp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(temp.name)/"test.sqlite3").as_posix()
os.environ["NETTYAN_CHARACTER_NAME"] = "Kadr"
from langchain_core.messages import AIMessage
from kadr.runtime import CourseRuntime

class FakeModel:
    def __init__(self,responses):
        self.responses = iter(responses)
        self.calls = 0
    def bind_tools(self,tools):
        return self
    def invoke(self,messages,**kwargs):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response,Exception):
            raise response
        return response

def answer(text="Проверено."):
    return AIMessage(content=text,usage_metadata={"input_tokens":100,"output_tokens":10,"total_tokens":110})

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        import uuid
        self.identity=uuid.uuid4().hex
    def test_memory_persists_and_does_not_cross_users(self):
        r=CourseRuntime(llm=FakeModel([]))
        self.assertTrue(r.save_note(self.identity,"Ремонтирует велосипед",True)["saved"])
        r.db.engine.dispose()
        other=CourseRuntime(llm=FakeModel([]))
        self.assertEqual(other.notes(self.identity)[0]["note"],"Ремонтирует велосипед")
        self.assertEqual(other.notes("f"*32),[])
    def test_save_requires_operator_consent(self):
        r=CourseRuntime(llm=FakeModel([]))
        self.assertFalse(r.save_note(self.identity,"Не сохранять",False)["saved"])
        self.assertEqual(r.notes(self.identity),[])
    def test_native_tool_receipt_and_dialogue(self):
        call=AIMessage(content="",tool_calls=[{"name":"save_note","args":{"note":"Зелёный велосипед"},"id":"call_test"}],usage_metadata={"input_tokens":100,"output_tokens":10,"total_tokens":110})
        model=FakeModel([call,answer("Заметка сохранена.")])
        r=CourseRuntime(llm=model)
        result=r.reply(self.identity,"Запомни велосипед",True)
        self.assertEqual(model.calls,2)
        self.assertTrue(result["tools"][0]["result"]["saved"])
        self.assertEqual(len(r.db.get_user_diags(r.user_id(self.identity),4)),2)
    def test_stop_blocks_requests_and_writes(self):
        model=FakeModel([answer()])
        r=CourseRuntime(llm=model)
        r.stop(self.identity)
        with self.assertRaises(ValueError): r.reply(self.identity,"Привет")
        self.assertFalse(r.save_note(self.identity,"Тест",True)["saved"])
        self.assertEqual(model.calls,0)
    def test_forget_removes_history_as_well_as_notes(self):
        r=CourseRuntime(llm=FakeModel([answer()]))
        r.save_note(self.identity,"Забыть меня",True)
        r.reply(self.identity,"Это тоже забыть")
        r.forget(self.identity)
        self.assertEqual(r.notes(self.identity),[])
        self.assertEqual(r.db.get_user_diags(r.user_id(self.identity),4),[])
    def test_budget_blocks_call(self):
        model=FakeModel([answer()])
        r=CourseRuntime(llm=model)
        r.limit_usd=0
        with self.assertRaises(ValueError): r.reply(self.identity,"Привет")
        self.assertEqual(model.calls,0)
    def test_failure_keeps_reservation_without_error_secret(self):
        r=CourseRuntime(llm=FakeModel([RuntimeError("sk-secret")]))
        before=r.spend()
        with self.assertRaises(RuntimeError) as error: r.reply(self.identity,"Привет")
        self.assertNotIn("sk-secret",str(error.exception))
        self.assertAlmostEqual(r.spend()-before,0.03)

if __name__ == "__main__":
    unittest.main()
