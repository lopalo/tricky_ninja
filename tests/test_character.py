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
        __builtin__.loader = mock.Mock()
        manager = mock.MagicMock()
        manager.map.__contains__ = mock.Mock(return_value=True)
        manager.npcs = {}
        self.char = char = character.Character(manager)
        char.actor = actor = mock.Mock()
        actor.getHpr = mock.Mock(return_value=(90, 30, 30))
        self.anim_mock = mock.Mock()
        actor.getAnimControl.return_value = self.anim_mock
        char.speed = 1
        char.hit_speed = 1
        char.post_hit_speed = 2
        char.hit_range = (4, 10)
        char.post_hit_range = (12, 18)
        S.ch_anim = {'walk_range': (100, 200)}
        char.idle_frame = 2323
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
        walking_states = []
        for _ in gen:
            walking_states.append(char.walking)
        self.assertListEqual([False, True, True, False, True], walking_states)
        exp = [
            mock.call(actor, 0.5, (180, 0, 0), (90, 0, 0)),
            mock.call(char.node, 1.0, (3, 4, 0)),
            mock.call(char.node, 1.0, (4, 4, 0)),
            mock.call(actor, 0.25, (45, 0, 0), (90, 0, 0)),
            mock.call(char.node, 1.4, (5, 3, 0))
        ]
        self.assertListEqual(exp, self.interval_mock.call_args_list)
        exp = [mock.call(True, 100, 200)]
        self.assertListEqual(exp, self.anim_mock.loop.call_args_list)
        self.assertListEqual([mock.call(0.5)],
                self.anim_mock.setPlayRate.call_args_list)
        self.assertEqual((5, 3), char.pos)
        self.assertEqual(3, char.manager.map.block.call_count)
        self.assertEqual(3, char.manager.map.unblock.call_count)

    def test_hit(self):
        char = self.char
        char.manager.npcs[3, 4] = target = mock.Mock()
        gen = char.do_hit()
        for _ in gen:
            pass
        exp = [
            mock.call('anim', playRate=1, startFrame=4, endFrame=10),
            mock.call('anim', playRate=2, startFrame=12, endFrame=18)
        ]
        self.assertListEqual(exp, char.actor.actorInterval.call_args_list)
        self.assertEqual(0, target.kill.call_count)
        char.action = None
        char.actor.actorInterval.reset_mock()
        char.manager.npcs[4, 3] = target
        self.assertEqual(0, target.kill.call_count)
        gen = char.do_hit()
        for _ in gen:
            pass
        exp = [
            mock.call('anim', playRate=1, startFrame=4, endFrame=10),
            mock.call('anim', playRate=2, startFrame=12, endFrame=18)
        ]
        self.assertListEqual(exp, char.actor.actorInterval.call_args_list)
        self.assertEqual(1, target.kill.call_count)


class TestPlayer(unittest.TestCase):
    maxDiff = None
    interval_mock = mock.Mock()

    @mock.patch('character.Actor')
    def setUp(self, actor):
        character.set_testing(True)
        __builtin__.S = mock.MagicMock()
        __builtin__.render = mock.Mock()
        __builtin__.loader = mock.Mock()
        __builtin__.base = mock.Mock()
        __builtin__.camera = mock.Mock()
        manager = mock.Mock()
        manager.map.__contains__ = mock.Mock(return_value=True)
        manager.npcs = {}
        self.pl = pl = character.Player(manager, (3, 3))
        pl.actor.getHpr = mock.Mock(return_value=(45, 30, 30))
        pl.actor.getAnimControl.return_value = self.anim_mock = mock.Mock()
        pl.speed = 1
        S.pl_anim = {
            'walk_range': (43, 46),
            'pre_jump_range': (32, 40),
            'pre_jump_speed': 4,
            'post_jump_range': (12, 30),
            'post_jump_speed': 2,
        }
        S.ch_anim = {'walk_range': (343, 400)}

    @mock.patch('character.LerpHprInterval', interval_mock)
    @mock.patch('character.LerpPosInterval', interval_mock)
    @mock.patch('character.ProjectileInterval', interval_mock)
    def test_jump(self):
        p = self.pl
        p.walk_pred = mock.Mock(return_value=True)
        p.manager.map.get_jump_field.return_value = ((3, 5),
                                                     (5, 3), (3, 1))
        loader.loadModel.return_value = pointer = mock.Mock()
        gen = p.do_jump()
        ret = next(gen)
        self.assertIsInstance(ret, character.events)
        self.assertIn(p.must_die_event, ret.items)
        gen.send('arrow_right')
        gen.send('arrow_right')
        gen.send('arrow_left')
        gen.send('space-up')
        exp = [
            mock.call(3, 5, 0.1),
            mock.call(5, 3, 0.1),
            mock.call(3, 1, 0.1),
            mock.call(5, 3, 0.1)
        ]
        self.assertListEqual(exp, pointer.setPos.call_args_list)
        S.player={'jump_height': 1}
        self.assertEqual(0, p.manager.map.block.call_count)
        for _ in gen:
            pass
        exp = [mock.call(True, 343, 400)]
        self.assertListEqual(exp, self.anim_mock.loop.call_args_list)
        self.assertListEqual([mock.call(0.5)],
                self.anim_mock.setPlayRate.call_args_list)
        exp = [
            mock.call(p.actor, 0.25, (90.0, 0, 0), (45, 0, 0)),
            mock.call(p.actor, (0, 0, 0), (0, 0, 0), 1, gravityMult=1),
            mock.call(p.node, 0.5, (4.0, 3.0, 0)),
            mock.call(p.node, 0.5, (5, 3, 0))
        ]
        self.assertListEqual(exp ,self.interval_mock.call_args_list)
        exp = [
            mock.call('anim', playRate=4, startFrame=32, endFrame=40),
            mock.call('anim', playRate=2, startFrame=12, endFrame=30)
        ]
        self.assertListEqual(exp, p.actor.actorInterval.call_args_list)
        self.assertEqual(1, p.manager.map.block.call_count)

if __name__ == '__main__':
    unittest.main()