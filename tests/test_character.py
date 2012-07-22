import sys
sys.path.insert(0, '')

import __builtin__
import unittest
from collections import deque
import mock
import character


class TestCharacter(unittest.TestCase):
    maxDiff = None
    interval_mock = mock.Mock()

    def setUp(self):
        self.interval_mock.reset_mock()
        character.set_testing(True)
        __builtin__.S = mock.MagicMock()
        __builtin__.render = mock.Mock()
        __builtin__.taskMgr = mock.Mock()
        manager = mock.Mock()
        self.char = char = character.Character(manager)
        char.actor = actor = mock.Mock()
        actor.getHpr = mock.Mock(return_value=(90, 30, 30))
        char.speed = 1
        char.pos = (3, 3)

    @mock.patch('character.LerpHprInterval', interval_mock)
    @mock.patch('character.LerpPosInterval', interval_mock)
    def test_walk(self):
        char = self.char
        actor = char.actor
        char.walk_pred = mock.Mock(return_value=True)
        seff = (((3, 4), True), ((4, 4), True), ((5, 3), True))
        char.get_next_pos = mock.Mock(side_effect=seff)
        gen = char.do_walk()
        ret = next(gen)
        self.assertIsInstance(ret, character.wait)
        self.assertEqual(.05, ret.seconds)
        for _ in gen:
            pass
        exp = [
            mock.call(actor, 0.5, (180, 0, 0), (90, 0, 0)),
            mock.call(char.node, 0.5, (3.0, 3.5, 0)),
            mock.call(char.node, 0.5, (3, 4, 0)),
            mock.call(char.node, 0.5, (3.5, 4.0, 0)),
            mock.call(char.node, 0.5, (4, 4, 0)),
            mock.call(actor, 0.25, (45, 0, 0), (90, 0, 0)),
            mock.call(char.node, 0.7, (4.5, 3.5, 0)),
            mock.call(char.node, 0.7, (5, 3, 0))
        ]
        self.assertListEqual(exp, self.interval_mock.call_args_list)
        self.assertEqual((5, 3), char.pos)
        self.assertEqual(3, char.manager.map.block.call_count)
        self.assertEqual(3, char.manager.map.unblock.call_count)


if __name__ == '__main__':
    unittest.main()