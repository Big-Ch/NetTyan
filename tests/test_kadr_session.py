import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kadr.session import GameSession
class SessionTests(unittest.TestCase):
    def test_cancelled_reply_cannot_start_speech(self):
        session=GameSession(Mock())
        session.cancel.set()
        with patch('kadr.session.synthesize') as tts,patch('kadr.session.play_local') as play:
            session.publish({'answer':'Устаревший ответ'},True)
        tts.assert_not_called();play.assert_not_called()
        self.assertEqual(session.version,0)
    def test_stop_cancels_body_voice_and_owner(self):
        runtime=Mock()
        session=GameSession(runtime)
        session.identity='a'*32
        with patch('kadr.session.stop_local_voice') as silence:
            session.stop('b'*32)
        self.assertTrue(session.cancel.is_set())
        runtime.minecraft.stop.assert_called_once()
        self.assertEqual(runtime.stop.call_count,2)
        silence.assert_called_once()
if __name__=='__main__':unittest.main()
