import sys
sys.path.insert(0, '')

import __builtin__
import unittest
from collections import deque
import mock
from character import NPC, Character
from map_model.map import Map
from manager import Manager


class TestNPC(unittest.TestCase):

    @mock.patch('manager.Map')
    @mock.patch('character.Player')
    @mock.patch('character.NPC')
    def setUp(self, map_mock, pl_mock, npc_mock):
        __builtin__.S = mock.MagicMock()
        __builtin__.render = mock.Mock()

        S.show_view_field = False
        S.alert_radius = 3
        S.npc = dict(
            excited_view_radius=3,
            excited_view_angle=88
        )

        manager = Manager('map')
        self.player = Character(manager)
        self.player.pos = (2, 2)
        manager.player = self.player
        self.npc1 = Character(manager)
        self.npc1.pos = (1, 1)
        self.npc1.actor = mock.Mock()
        self.npc2 = Character(manager)
        self.npc2.pos = (3, 1)
        self.npc2.actor = mock.Mock()
        manager.npcs = {(1, 1): self.npc1, (3, 1): self.npc2}
        top = [
            'ss ss ss ss ss ss',
            'ss ss ss ss ss ss',
            'ss ss ss ss ss ss',
            'ss ss ss ss ss ss',
            'ss ss ss ss ss ss'
        ]
        data = dict(
            substrate_texture='grass',
            substrate_actions='free',
            action_groups={
                'walk':['walk'],
                'jump':['jump'],
                'free':['jump', 'walk']
            },
            definitions={},
            topology=top
        )
        manager.map = Map(data=data, check=False)

    def test_face_to_player(self):
        npc = self.npc1
        npc.actor.getHpr = mock.Mock(return_value=(180, 0, 0))
        self.assertFalse(NPC.face_to_player.__get__(npc))
        npc.actor.getHpr = mock.Mock(return_value=(135, 0, 0))
        self.assertTrue(NPC.face_to_player.__get__(npc))
        npc.actor.getHpr = mock.Mock(return_value=(0, 0, 0))
        self.assertFalse(NPC.face_to_player.__get__(npc))
        npc.actor.getHpr = mock.Mock(return_value=(270, 0, 0))
        self.assertFalse(NPC.face_to_player.__get__(npc))

    def test_in_view_field(self):
        npc = self.npc1
        npc.pos, npc.view_radius, npc.view_angle = (0, 0), 3, 120
        npc.actor.getHpr = mock.Mock(return_value=(0, 0, 0))
        pl = self.player
        meth = NPC.__dict__['in_view_field']
        self.assertFalse(meth(npc, pl))
        npc.actor.getHpr = mock.Mock(return_value=(180, 0, 0))
        self.assertTrue(meth(npc, pl))

    def test_get_next_pos(self):
        npc = self.npc1
        pl = self.player
        npc.get_action = mock.Mock(return_value='walk')
        npc.target = (0, 3)
        meth = NPC.__dict__['get_next_pos']
        self.assertEqual(((0, 2), True), meth(npc))
        npc.target = pl
        pl.pos = (3, 0)
        self.assertEqual(((2, 0), True), meth(npc))
        pl.pos = (1, 0)
        self.assertEqual(((1, 0), False), meth(npc))

    def test_get_action(self):
        npc = self.npc1
        pl = self.player
        route = npc.route = deque(((0, 0), (4, 1), (1, 1)))
        npc.in_view_field = mock.Mock(return_value=False)
        npc.target = route[0]
        meth = NPC.__dict__['get_action']
        self.assertEqual('walk', meth(npc))
        self.assertEqual((0, 0), npc.target)
        npc.pos = (0, 0)
        self.assertEqual('walk', meth(npc))
        self.assertEqual((4, 1), npc.target)
        npc.pos = (4, 1)
        self.assertEqual('walk', meth(npc))
        self.assertEqual((1, 1), npc.target)
        npc.in_view_field = mock.Mock(return_value=True)
        self.assertEqual('walk', meth(npc))
        self.assertIs(pl, npc.target)
        npc.pos = (1, 1)
        npc.face_to_player = False
        self.assertEqual('walk', meth(npc))
        self.assertIs(pl, npc.target)
        npc.face_to_player = True
        self.assertEqual('hit', meth(npc))
        self.assertIs(pl, npc.target)
        pl.dead = True
        self.assertEqual('walk', meth(npc))
        self.assertEqual((0, 0), npc.target)
        npc.target = pl
        pl.dead = False
        npc.in_view_field = mock.Mock(return_value=False)
        self.assertEqual('walk', meth(npc))
        self.assertEqual(pl.pos, npc.target)

    def test_alert1(self):
        npc1 = self.npc1
        npc2 = self.npc2
        pl = self.player
        npc1.target = npc2.target = None
        npc1.view_rasius = npc2.view_radius = 1
        npc1.view_angle = npc2.view_angle = 50
        npc1.in_view_field = mock.Mock(return_value=True)
        meth = NPC.__dict__['get_action']
        self.assertEqual('walk', meth(npc1))
        self.assertEqual(3, npc1.view_radius)
        self.assertEqual(88, npc1.view_angle)
        self.assertEqual(3, npc2.view_radius)
        self.assertEqual(88, npc2.view_angle)
        self.assertIs(pl, npc1.target)
        self.assertIs(pl, npc2.target)

    def test_alert2(self):
        npc1 = self.npc1
        npc2 = self.npc2
        pl = self.player
        npc1.target = npc2.target = None
        npc1.view_rasius = npc2.view_radius = 1
        npc1.view_angle = npc2.view_angle = 50
        npc1.in_view_field = mock.Mock(return_value=True)
        meth = NPC.__dict__['get_action']
        npc2.pos = (5, 0)
        self.assertEqual('walk', meth(npc1))
        self.assertEqual(3, npc1.view_radius)
        self.assertEqual(88, npc1.view_angle)
        self.assertEqual(1, npc2.view_radius)
        self.assertEqual(50, npc2.view_angle)
        self.assertIs(pl, npc1.target)
        self.assertIsNone(npc2.target)

if __name__ == '__main__':
    unittest.main()