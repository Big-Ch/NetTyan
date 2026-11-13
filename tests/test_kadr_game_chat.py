import sys,unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kadr.club_dialogue import ClubDialogue
from kadr.game_chat import GameChat,player_message
class ChatParsingTests(unittest.TestCase):
    def test_player_message(self):
        self.assertEqual(player_message('§a<Guest_1> Кадр, привет'),('Guest_1','Кадр, привет'))
    def test_diagnostics_are_not_players(self):
        self.assertIsNone(player_message('[Alto Clef] Task finished'))
        self.assertIsNone(player_message('[Server] restart in 5'))

    def test_invitation_requires_verified_approach(self):
        bridge=Mock()
        bridge.recent_chat.return_value=[]
        initial={'inGame':True,'xyz':[0,70,0],'players':[{'name':'Guest','distance':'8.0','pos':'8.0,70.0,0.0'}]}
        arrived={**initial,'xyz':[5,70,0],'players':[{'name':'Guest','distance':'3.0','pos':'8.0,70.0,0.0'}]}
        bridge.status.side_effect=[initial,initial,arrived]
        session=Mock(active=False)
        session.bridge.return_value=bridge
        chat=GameChat.__new__(GameChat)
        chat.session=session
        chat.cancel=Mock()
        chat.cancel.is_set.return_value=False
        chat.cancel.wait.side_effect=[False,False,True]
        chat._run(False,True)
        bridge.move_toward.assert_called_once_with(initial,[8.0,70.0,0.0],run=True)
        bridge.say.assert_called_once()
        invitation=bridge.say.call_args.args[0]
        self.assertTrue(invitation.startswith('Guest, '), invitation)
        self.assertIn('Можешь сказать «пас».',invitation)

    def test_new_homework_uses_different_recent_builds(self):
        dialogue=ClubDialogue()
        answers=[dialogue.homework(), dialogue.invitation('Guest'), dialogue.homework()]
        builds=[next(build for build in dialogue.BUILDS if build+'.' in answer) for answer in answers]
        self.assertEqual(len(set(builds)), 3)
        self.assertTrue(all('На своём участке' in answer and len(answer)<=220 for answer in answers))

    def test_repeated_homework_requests_reach_text_and_voice_without_api(self):
        bridge=Mock()
        first='<Guest> Тайлер, дай домашку'
        second='<Guest> Тайлер, другую домашку'
        bridge.recent_chat.side_effect=[[],[first],[first,second]]
        session=Mock(active=False)
        session.bridge.return_value=bridge
        chat=GameChat.__new__(GameChat)
        chat.session=session
        chat.cancel=Mock()
        chat.cancel.is_set.return_value=False
        chat.cancel.wait.side_effect=[False,False,True]
        chat.identity=Mock(return_value='guest-identity')
        chat._on_community=Mock(return_value=True)
        chat._speak_in_game=Mock(return_value=True)
        with patch('kadr.game_chat.time.monotonic', side_effect=[100,100,100,100,106,106,106]):
            chat._run(False, community_only=True)
        answers=[call.args[0] for call in bridge.say.call_args_list]
        self.assertEqual(len(answers), 2)
        self.assertNotEqual(*answers)
        self.assertEqual([call.args[1] for call in chat._speak_in_game.call_args_list], answers)
        session.runtime.reply.assert_not_called()
if __name__=='__main__':unittest.main()
