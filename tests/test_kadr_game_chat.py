import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kadr.game_chat import player_message
class ChatParsingTests(unittest.TestCase):
    def test_player_message(self):
        self.assertEqual(player_message('§a<Guest_1> Кадр, привет'),('Guest_1','Кадр, привет'))
    def test_diagnostics_are_not_players(self):
        self.assertIsNone(player_message('[Alto Clef] Task finished'))
        self.assertIsNone(player_message('[Server] restart in 5'))
if __name__=='__main__':unittest.main()
