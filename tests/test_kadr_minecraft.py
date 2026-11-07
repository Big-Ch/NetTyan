"""Controller contract checks. These do not claim movement in a real game."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kadr.minecraft import MinecraftBridge, coordinates

class MinecraftTests(unittest.TestCase):
    def bridge(self):
        with patch('kadr.minecraft.JavaGateway'):
            bridge=MinecraftBridge()
        bridge.gateway=Mock()
        bridge.gateway.entry_point.getGameState.return_value={'inGame':True,'self':{'pos':'1,5,64,0,-2,5'}}
        bridge.gateway.entry_point.getOpenScreen.return_value={'open':False}
        bridge.gateway.entry_point.getInventoryFull.return_value={'slots':[]}
        bridge.gateway.entry_point.hasActiveTask.return_value=False
        return bridge
    def test_both_coordinate_locales(self):
        self.assertEqual(coordinates('1,5,64,0,-2,5'),[1.5,64.0,-2.5])
        self.assertEqual(coordinates('1.5,64.0,-2.5'),[1.5,64.0,-2.5])
    def test_rejection_does_not_become_success(self):
        bridge=self.bridge()
        bridge.gateway.entry_point.RunInnerCommand.side_effect=RuntimeError('controller unavailable')
        self.assertFalse(bridge.walk(4,0)['accepted'])
        self.assertIsNone(bridge.goal)
    def test_queue_receipt_does_not_mean_arrival(self):
        bridge=self.bridge()
        result=bridge.walk(4,0)
        self.assertTrue(result['accepted'])
        self.assertFalse(result['arrival_confirmed'])
        self.assertFalse(bridge.status()['arrival_confirmed'])
    def test_invalid_distance_never_reaches_controller(self):
        bridge=self.bridge()
        for dx in (5,True,2.5):
            self.assertFalse(bridge.walk(dx,0)['accepted'])
        bridge.gateway.entry_point.RunInnerCommand.assert_not_called()
    def test_inventory_is_proof_for_obtain(self):
        bridge=self.bridge()
        self.assertTrue(bridge.obtain('crafting_table',1)['accepted'])
        self.assertFalse(bridge.status()['task']['completed'])
        bridge.gateway.entry_point.getInventoryFull.return_value={'slots':[{'empty':False,'item':'minecraft:crafting_table','count':1}]}
        self.assertTrue(bridge.status()['task']['completed'])

if __name__=='__main__':unittest.main()
