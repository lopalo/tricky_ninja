import sys
sys.path.insert(0, '')

import __builtin__
import unittest
from collections import deque, defaultdict
import mock
from character.player import Player
from character.action import events
from character import action

class TestPlayer(unittest.TestCase):
    maxDiff = None
    interval_mock = mock.Mock()

    @mock.patch('character.player.Actor')
    def setUp(self, actor):
        self.interval_mock.reset_mock()
        action.set_testing(True)
        __builtin__.S = mock.MagicMock()
        __builtin__.render = mock.Mock()
        __builtin__.loader = mock.Mock()
        __builtin__.base = mock.Mock()
        __builtin__.camera = mock.Mock()
        manager = mock.Mock()
        manager.map.__contains__ = mock.Mock(return_value=True)
        manager.npcs = {}
        manager.bodies = {}
        self.pl = pl = Player(manager, (3, 3))
        pl.actor.getHpr = mock.Mock(return_value=(45, 30, 30))
        pl.actor.getAnimControl.return_value = self.anim_mock = mock.Mock()
        pl.speed = 1
        S.pl_anim = {
            'walk_range': (43, 46),
            'pre_jump_range': (32, 40),
            'pre_jump_speed': 4,
            'post_jump_range': (12, 30),
            'post_jump_speed': 2,
            'pick_up_speed': 10,
            'pick_up_range': (109, 201),
            'body_moving_range': (1329, 2373)
        }
        S.player = defaultdict(int)
        S.player['body_moving_speed'] = .2
        S.ch_anim = {'walk_range': (343, 400)}

    @mock.patch('character.char.LerpHprInterval', interval_mock)
    @mock.patch('character.player.LerpPosInterval', interval_mock)
    @mock.patch('character.player.ProjectileInterval', interval_mock)
    def test_jump(self):
        p = self.pl
        p.walk_pred = mock.Mock(return_value=True)
        p.manager.map.get_jump_field.return_value = ((3, 5),
                                                     (5, 3), (3, 1))
        loader.loadModel.return_value = pointer = mock.Mock()
        gen = p.do_jump()
        ret = next(gen)
        self.assertIsInstance(ret, events)
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

    @mock.patch('character.char.LerpHprInterval', interval_mock)
    @mock.patch('character.player.LerpPosInterval', interval_mock)
    def test_body_moving(self):
        p = self.pl
        p.walk_pred = mock.Mock(return_value=True)
        p.manager.bodies[4, 2] = body = mock.Mock()
        body.poses = (4, 2)
        gen = p.do_move_body()
        p.must_die, p.captured_body = False, True
        next(gen)
        self.assertEqual(1, body.hide.call_count)
        self.assertEqual(0, body.bind.call_count)
        ret = next(gen)
        self.assertEqual(1, body.bind.call_count)
        self.assertIsInstance(ret, events)
        self.assertEqual((p.must_die_event,
                          p.release_body_event,
                          p.continue_move_body_event), ret.items)
        seff = ((4, 3), (5, 3))
        p.get_next_pos = mock.Mock(side_effect=seff)
        rpath = mock.Mock(return_value=((3, 2), (2, 2), (2, 3)))
        p.manager.map.get_radial_path = rpath
        gen.send(p.continue_move_body_event)
        next(gen)
        next(gen)
        p.manager.map.get_radial_path = mock.Mock(return_value=[])
        ret = next(gen)
        self.assertNotIsInstance(ret, events)
        p.get_next_pos = mock.Mock(return_value=None)
        ret = next(gen)
        self.assertIsInstance(ret, events)
        gen.send(p.must_die_event)
        self.assertEqual(3, body.update_poses.call_count)
        self.assertEqual(2, body.hide.call_count)
        self.assertEqual(0, body.unbind.call_count)
        with self.assertRaises(StopIteration):
            next(gen)
        self.assertEqual(1, body.unbind.call_count)
        exp = [
            mock.call(p.actor, 1.25, (0, 0, 0), (45, 0, 0)),
            mock.call(p.actor, 2.5, (-45, 0, 0), (45, 0, 0)),
            mock.call(p.node, 5.0, (4, 3, 0))
        ]
        self.assertListEqual(exp, self.interval_mock.call_args_list)

if __name__ == '__main__':
    unittest.main()