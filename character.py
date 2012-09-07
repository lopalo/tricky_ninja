import sys
from functools import wraps
from collections import deque
from math import cos, sin, radians, atan2, degrees, hypot
from types import GeneratorType
from direct.interval.LerpInterval import (
    LerpPosInterval, LerpHprInterval,
    LerpNodePathInterval, LerpColorScaleInterval
)
from direct.interval.ProjectileInterval import ProjectileInterval
from direct.interval.ActorInterval import ActorInterval
from direct.actor.Actor import Actor


_testing = False

def set_testing(value):
    global _testing
    _testing = value


def action(name):
    actions = sys._getframe(1).f_locals['actions']
    assert name not in actions
    def wrapper(func):
        @wraps(func)
        def wrap(char, *args, **kwargs):
            assert isinstance(char, Character)
            assert char.action == None
            char.action = name
            gen = func(char, *args, **kwargs)
            assert isinstance(gen, GeneratorType)
            if _testing:
                return gen
            _runner(char, gen, None)
        actions[name] = wrap
        return wrap
    return wrapper


def _runner(char, gen, send_value=None):
    try:
        yielded = gen.send(send_value)
    except StopIteration:
        char.action = None
        return
    if isinstance(yielded, wait):
        def callback(task):
            _runner(char, gen)
        taskMgr.doMethodLater(yielded.seconds, callback, str(id(wait)))
    elif isinstance(yielded, (LerpNodePathInterval, ActorInterval)):
        def callback():
            _runner(char, gen)
        key = str(id(gen))
        base.acceptOnce(key, callback)
        yielded.setDoneEvent(key)
        yielded.start()
    elif isinstance(yielded, events):
        items = yielded.items
        def callback(e_name):
            for ev in items:
                base.ignore(ev)
            _runner(char, gen, e_name)
        for i in items:
            base.acceptOnce(i, callback, [i])
    else:
        raise Exception('Unsupported type ' + type(yielded).__name__)


class wait:

    def __init__(self, seconds):
        self.seconds = seconds


class events:

    def __init__(self, *items):
        self.items = items


class Character(object):
    model = 'ninja'
    actions = {}

    #(forward, right)
    angle_table = {
        (1, 0): 0,
        (-1, 0): 180,
        (0, 1): -90,
        (0, -1): 90,
        (1, 1): -45,
        (-1, -1): 135,
        (-1, 1): -135,
        (1, -1): 45
    }
    reverse_angle_table = dict((v, k) for k, v in angle_table.items())

    def __init__(self, manager):
        self.action = None
        self.must_die = False
        self.dead = False
        self.fall_forward = True
        self.walking = False
        self.manager = manager
        self.node = node = render.attachNewNode(str(id(self)))
        node.reparentTo(manager.main_node)

    def __nonzero__(self):
        return not self.dead

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        assert value in self.manager.map
        self._pos = value

    def walk_pred(self, pos):
        map = self.manager.map
        return (map.is_available(pos) and
                'walk' in map[pos]['actions'] and
                self.manager.is_available(pos))

    @property
    def actor_angle(self):
        return int(self.actor.getHpr()[0] - 90) % 360

    def angle_to_pos(self, diff): # diff = 0 is forward
        angle = int(self.actor.getHpr()[0] + diff - 90) % 360
        angle = angle if angle <= 180 else angle - 360
        diff = self.reverse_angle_table[angle]
        pos = self.pos[0] + diff[0], self.pos[1] - diff[1]
        return pos

    @action('walk')
    def do_walk(self):
        # 'yield wait()' need for reading right direction
        # if player pressed 2 arrow keys
        yield wait(.05)
        map = self.manager.map
        actor = self.actor
        anim = actor.getAnimControl('anim')
        sp = float(self.speed)
        anim.setPlayRate(sp / 2)
        wr = S.ch_anim['walk_range']
        anim.loop(True, wr[0], wr[1])
        while True:
            if sp != float(self.speed): # npc can change speed
                break
            next_pos, walk = self.get_next_pos()
            if self.must_die or next_pos is None:
                break
            shift = next_pos[1] - self.pos[1], next_pos[0] - self.pos[0]
            angle = (self.angle_table[shift] + 180) % 360
            c_angle = actor.getHpr()[0] % 360
            d_angle = angle - c_angle
            if d_angle != 0:
                if abs(d_angle) > 180:
                    angle = angle - 360 if d_angle > 0 else angle + 360
                dur = float(abs(angle - c_angle)) / 360 / sp * 2
                interval = LerpHprInterval(actor, dur, (angle, 0, 0),
                                                       (c_angle, 0, 0))
                yield interval

            if not walk or not self.walk_pred(next_pos):
                break
            if isinstance(self, Player) and not self.get_next_pos()[0]:
                break
            dur = 1.4 / sp if all(shift) else 1.0 / sp
            interval = LerpPosInterval(self.node, dur, next_pos + (0,))
            map.block(next_pos)
            self.walking = True
            yield interval
            self.pos = next_pos
            map.unblock(self.pos)
            self.walking = False
        anim.pose(self.idle_frame)

    @action('hit')
    def do_hit(self):
        actor = self.actor
        interval = actor.actorInterval(
            'anim',
            playRate=self.hit_speed,
            startFrame=self.hit_range[0],
            endFrame=self.hit_range[1]
        )
        yield interval
        if self.must_die:
            return
        angle = self.actor_angle
        target_coord = self.angle_to_pos(0)
        if target_coord in self.manager.npcs:
            self.manager.npcs[target_coord].kill(angle)
        elif self.manager.player.pos == target_coord:
            self.manager.player.kill(angle)
        interval = actor.actorInterval(
            'anim',
            playRate=self.post_hit_speed,
            startFrame=self.post_hit_range[0],
            endFrame=self.post_hit_range[1]
        )
        yield interval
        actor.pose('anim', self.idle_frame)

    def kill(self, hit_angle):
        if not self:
            return
        self.must_die = True
        hit_angle = int(hit_angle % 360)
        diff = abs(self.actor_angle - hit_angle)
        if diff > 180:
            diff = abs(diff - 360)
        self.fall_forward = diff < 90


class Player(Character):
    actions = Character.actions.copy()

    release_body_event = 'release_body_event'
    continue_move_body_event = 'continue_move_body_event'
    must_die_event = 'must_die_event'

    def __init__(self, manager, pos):
        super(Player, self).__init__(manager)

        self.captured_body = False
        self.speed = S.player['speed']
        self.idle_frame = S.player['idle_frame']
        self.hit_range = S.pl_anim['hit_range']
        self.hit_speed = S.pl_anim['hit_speed']
        self.post_hit_range = S.pl_anim['post_hit_range']
        self.post_hit_speed = S.pl_anim['post_hit_speed']

        self.move_direction = [0, 0] #[forward, right]
        self.actor = actor = Actor(S.model(self.model),
                                    {'anim': S.model(self.model)})
        self.actor.reparentTo(self.node)
        actor.setScale(S.model_size(self.model))
        actor.setTransparency(True)
        actor.setTexture(loader.loadTexture(
                            S.texture(S.player['texture'])), 1)
        self.pos = self.init_position = tuple(pos)
        self.node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', self.idle_frame)
        actor.setBlend(frameBlend=True)
        self.set_camera()
        self.set_arrow_handlers()
        self.set_control()

    def set_camera(self):
        camera.reparentTo(self.node)
        self.cam_distance = S.camera['init_distance']
        self.cam_angle = S.camera['init_vertical_angle']
        def recalc():
            pitch = -S.camera['horizontal_angle']
            min_d = S.camera['min_distance']
            max_d = S.camera['max_distance']
            yaw = self.cam_angle
            self.cam_distance = min(max(self.cam_distance, min_d), max_d)
            dist = self.cam_distance
            z = dist * sin(radians(-pitch))
            xy_dist = dist * cos(radians(-pitch))
            x = xy_dist * cos(radians(yaw))
            y = xy_dist * sin(radians(yaw))
            camera.setPosHpr(x, y, z, 90 + yaw, pitch, 0)
        def incr_angle():
            self.cam_angle += S.camera['vertical_angle_step']
            recalc()
        base.accept('z', incr_angle)
        base.accept('z-repeat', incr_angle)
        def decr_angle():
            self.cam_angle -= S.camera['vertical_angle_step']
            recalc()
        base.accept('x', decr_angle)
        base.accept('x-repeat', decr_angle)
        def incr_dist():
            self.cam_distance += S.camera['distance_step']
            recalc()
        base.accept('a', incr_dist)
        base.accept('a-repeat', incr_dist)
        def decr_dist():
            self.cam_distance -= S.camera['distance_step']
            recalc()
        base.accept('s', decr_dist)
        base.accept('s-repeat', decr_dist)
        recalc()

    def set_arrow_handlers(self):
        def common_handler():
            if self.captured_body:
                messenger.send(self.continue_move_body_event)
            else:
                self.update_action('walk')
        def up():
            self.move_direction[0] = 1
            common_handler()
        def up_up():
            self.move_direction[0] = 0
        base.accept('arrow_up', up)
        base.accept('arrow_up-up', up_up)
        def down():
            self.move_direction[0] = -1
            common_handler()
        def down_up():
            self.move_direction[0] = 0
        base.accept('arrow_down', down)
        base.accept('arrow_down-up', down_up)
        def right():
            self.move_direction[1] = 1
            common_handler()
        def right_up():
            self.move_direction[1] = 0
        base.accept('arrow_right', right)
        base.accept('arrow_right-up', right_up)
        def left():
            self.move_direction[1] = -1
            common_handler()
        def left_up():
            self.move_direction[1] = 0
        base.accept('arrow_left', left)
        base.accept('arrow_left-up', left_up)

    def remove_arrow_handlers(self):
        base.ignore('arrow_up')
        base.ignore('arrow_up-up')
        base.ignore('arrow_down')
        base.ignore('arrow_down-up')
        base.ignore('arrow_right')
        base.ignore('arrow_right-up')
        base.ignore('arrow_left')
        base.ignore('arrow_left-up')

    def set_control(self):
        def space_down():
            self.update_action('jump')
        base.accept('space', space_down)
        base.accept('k', self.kill)
        def h_down():
            self.update_action('hit')
        base.accept('h', h_down)
        def b_down():
            self.captured_body = True
            self.update_action('move_body')
        base.accept('b', b_down)
        def b_up():
            self.captured_body = False
            messenger.send(self.release_body_event)
        base.accept('b-up', b_up)

    def kill(self, hit_angle):
        if not self:
            return
        super(Player, self).kill(hit_angle)
        messenger.send(self.must_die_event)

    def update_action(self, action=None):
        #calls in every frame and by some
        #events('arrows'...)

        if not self:
            return
        assert action in self.actions or action == None
        if self.action is not None:
            return
        if self.must_die:
            self.actions['die'](self)
            return
        if action is not None:
            self.actions[action](self)
        elif tuple(self.move_direction) != (0, 0):
            self.actions['walk'](self)

    def get_next_pos(self):
        move_dir = tuple(self.move_direction)
        map = self.manager.map
        pos = self.pos
        if move_dir == (0, 0):
            return None, False
        directions = deque((
            ('right'),
            ('right-bottom'),
            ('bottom'),
            ('bottom-left'),
            ('left'),
            ('left-top'),
            ('top'),
            ('top-right')
        ))
        nbs = dict(map.neighbors(pos, True, True))
        shift = (0, 0)
        angle = self.cam_angle + 180

        dir_angle = self.angle_table[move_dir]
        if dir_angle is not None:
            angle += dir_angle
            angle = angle % 360
            for a in range(-22, 360, 45):
                start, end = a, a + 45
                if start <= angle < end:
                    direction = directions[0]
                    walk = direction in nbs
                    break
                directions.rotate(1)
            shift = map._neighbors[direction]
        new_pos = pos[0] + shift[0], pos[1] + shift[1]
        if not walk:
            return new_pos, False

        if map.check_square(pos, new_pos, self.walk_pred):
            return new_pos, True
        return new_pos, False

    @action('jump')
    def do_jump(self):
        map = self.manager.map
        pred = lambda pos: 'jump' in map[pos]['actions']
        field = deque(map.get_jump_field(self.pos))
        if not field:
            return
        pointer = loader.loadModel(S.model('plane'))
        texture = loader.loadTexture(
                    S.texture(S.player['pointer_texture']))
        pointer.setTexture(texture)
        pointer.setTransparency(True)
        pointer.setHpr(0, -90, 0)
        pointer.reparentTo(self.manager.main_node)
        while True:
            pos = field[0]
            pointer.setPos(pos[0], pos[1], 0.1)
            val = yield events('arrow_left', 'arrow_left-repeat',
                               'arrow_right', 'arrow_right-repeat',
                               'space-up', self.must_die_event)
            if val in (self.must_die_event, 'space-up'):
                break
            elif val in ('arrow_left', 'arrow_left-repeat'):
                field.rotate(1)
            elif val in ('arrow_right', 'arrow_right-repeat'):
                field.rotate(-1)
            else:
                raise Exception('Unknown event')
        self.set_arrow_handlers()
        pointer.removeNode()
        if self.must_die:
            return
        actor = self.actor
        sp = float(self.speed)
        v = pos[0] - self.pos[0], pos[1] - self.pos[1]
        dist = float(hypot(v[0], v[1]))
        angle = (degrees(atan2(v[1], v[0])) + 90) % 360
        c_angle = actor.getHpr()[0] % 360
        d_angle = angle - c_angle
        if d_angle != 0:
            if abs(d_angle) > 180:
                angle = angle - 360 if d_angle > 0 else angle + 360
            dur = float(abs(angle - c_angle)) / 360 / sp * 2
            interval = LerpHprInterval(actor, dur, (angle, 0, 0),
                                                    (c_angle, 0, 0))
            anim = actor.getAnimControl('anim')
            anim.setPlayRate(sp / 2)
            wr = S.ch_anim['walk_range']
            anim.loop(True, wr[0], wr[1])
            yield interval
        if not self.walk_pred(pos):
            actor.pose('anim', self.idle_frame)
            return
        map.block(pos)
        wr = S.pl_anim['pre_jump_range']
        interval = actor.actorInterval(
            'anim',
            playRate=S.pl_anim['pre_jump_speed'],
            startFrame=wr[0], endFrame=wr[1]
        )
        yield interval
        interval = ProjectileInterval(actor, (0, 0, 0),
                    (0, 0, 0), 1, gravityMult=S.player['jump_height'])
        interval.start()
        mid_pos = (float(self.pos[0] + pos[0]) / 2,
                   float(self.pos[1] + pos[1]) / 2)
        interval = LerpPosInterval(self.node, 0.5, mid_pos + (0,))
        yield interval
        self.pos = pos
        map.unblock(self.pos)
        interval = LerpPosInterval(self.node, 0.5, pos + (0,))
        yield interval
        wr = S.pl_anim['post_jump_range']
        interval = actor.actorInterval(
            'anim',
            playRate=S.pl_anim['post_jump_speed'],
            startFrame=wr[0], endFrame=wr[1]
        )
        yield interval
        yield wait(0.1)
        actor.pose('anim', self.idle_frame)

    @action('die')
    def do_die(self):
        self.dead = True
        self.must_die = False
        actor = self.actor
        ds = S.ch_anim['death_speed']
        dr = (S.ch_anim['forward_death_range'] if self.fall_forward
                                else S.ch_anim['backward_death_range'])
        interval = actor.actorInterval(
            'anim', playRate=ds,
            startFrame=dr[0], endFrame=dr[1]
        )
        interval.start()
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 0))
        yield interval
        yield wait(1)
        init_pos = tuple(self.init_position)
        if (not self.manager.map.is_available(init_pos) or
            not self.manager.is_available(init_pos)):
                return # TODO: maybe delete player
        self.dead = False
        self.pos = init_pos
        self.node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', self.idle_frame)
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 1))
        yield interval

    @action('move_body')
    def do_move_body(self):
        map = self.manager.map
        bpos = self.angle_to_pos(0)
        if not bpos in self.manager.bodies:
            return
        body = self.manager.bodies[bpos]
        if not body.check_poses(bpos, self.actor_angle):
            return
        body.hide() # should be faster than pick-up animation
        actor = self.actor
        anim = actor.getAnimControl('anim')
        interval = actor.actorInterval(
            'anim',
            playRate=S.pl_anim['pick_up_speed'],
            startFrame=S.pl_anim['pick_up_range'][0],
            endFrame=S.pl_anim['pick_up_range'][1]
        )
        yield interval
        body.bind(self)
        while not self.must_die and self.captured_body:
            val = yield events(self.must_die_event, self.release_body_event,
                                                self.continue_move_body_event)
            if val != self.continue_move_body_event:
                break
            yield wait(.05)
            sp = float(S.player['body_moving_speed'])
            anim.setPlayRate(sp / 2)
            wr = S.pl_anim['body_moving_range']
            anim.loop(True, wr[0], wr[1])
            while not self.must_die and self.captured_body:
                next_pos, walk = self.get_next_pos()
                if self.must_die or next_pos is None:
                    break
                shift = next_pos[1] - self.pos[1], next_pos[0] - self.pos[0]
                new_bpos = self.pos[0] - shift[1], self.pos[1] - shift[0]
                angle = self.angle_table[shift] % 360
                if not body.check_poses(new_bpos, angle - 90):
                    break
                c_angle = actor.getHpr()[0] % 360
                d_angle = angle - c_angle
                if d_angle != 0:
                    if abs(d_angle) > 180:
                        angle = angle - 360 if d_angle > 0 else angle + 360
                    dur = float(abs(angle - c_angle)) / 360 / sp * 8
                    interval = LerpHprInterval(actor, dur, (angle, 0, 0),
                                                        (c_angle, 0, 0))
                    yield interval
                body.update_poses()
                if not walk or not self.walk_pred(next_pos):
                    break
                if not self.get_next_pos()[0]:
                    break
                dur = 1.4 / sp if all(shift) else 1.0 / sp
                interval = LerpPosInterval(self.node, dur, next_pos + (0,))
                map.block(next_pos)
                self.walking = True
                yield interval
                self.pos = next_pos
                map.unblock(self.pos)
                self.walking = False
                body.update_poses()
            anim.pose(S.player['body_captured_frame'])
        yield body.hide(False)
        body.unbind()


class NPC(Character):
    actions = Character.actions.copy()

    def __init__(self, manager, texture, route, **spam):
        super(NPC, self).__init__(manager)

        self.view_radius = S.npc['normal_view_radius']
        self.view_angle = S.npc['normal_view_angle']
        self.speed = S.npc['speed']
        self.idle_frame = S.npc['idle_frame']
        self.hit_range = S.npc_anim['hit_range']
        self.hit_speed = S.npc_anim['hit_speed']
        self.post_hit_range = S.npc_anim['post_hit_range']
        self.post_hit_speed = S.npc_anim['post_hit_speed']

        self.actor = actor = Actor(S.model(self.model),
                                    {'anim': S.model(self.model)})
        self.actor.reparentTo(self.node)
        actor.setTransparency(True)
        actor.setScale(S.model_size(self.model))
        actor.setTexture(loader.loadTexture(
                            S.texture(texture)), 1)
        self.init_position = self.pos = route[0]
        self.node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', S.npc['idle_frame'])
        actor.setBlend(frameBlend=True)
        ##########
        self.route = deque(route)
        self.target = route[0]

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        assert value in self.manager.map
        if hasattr(self, '_pos'):
            del self.manager.npcs[self._pos]
        self._pos = value
        self.manager.npcs[self._pos] = self

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        assert isinstance(value, (tuple, Player))
        self._target = value

    def get_next_pos(self):
        if self.get_action() != 'walk':
            return None, False
        manager = self.manager
        map = manager.map
        target = self.target
        end_pos = target if isinstance(target, tuple) else target.pos
        # TODO: maybe remove corpse occupation check
        pred = lambda pos: ('walk' in map[pos]['actions'] and
                            map.is_available(pos) and
                            (pos not in manager.npcs or
                            manager.npcs[pos].walking) and
                            pos not in manager.bodies)
        path = map.get_path(self.pos, end_pos, pred)
        if not path:
            return None, False
        elif len(path) == 1 and target is self.manager.player:
            return path[0], False
        else:
            return path[0], True

    def get_action(self):
        player = self.manager.player
        if self.target is player:
            if not self.in_view_field(player):
                self.target = player.pos
                return 'walk'
            if not player:
                self.route.rotate(-1)
                self.target = self.route[0]
                return 'walk'
            length = hypot(self.pos[0] - player.pos[0],
                           self.pos[1] - player.pos[1])
            if length < 1.5:
                if self.face_to_player and player:
                    return 'hit'
                else:
                    return 'walk'
            else:
                return 'walk'
        else:
            #TODO: check if corpse is in view_field
            if player and self.in_view_field(player):
                #TODO: if corpse then target is not the player
                self.manager.alert(self.pos)
                return 'walk'
            if self.pos == self.target:
                self.route.rotate(-1)
                self.target = self.route[0]
            return 'walk'

    def update_action(self):
        if self.action is not None:
            return
        action = self.get_action()
        assert action in self.actions
        if self.must_die:
            self.actions['die'](self)
            return
        self.actions[action](self)

    def in_view_field(self, char):
        assert isinstance(char, Character)
        map = self.manager.map
        radius, c_angle = self.view_radius, self.view_angle
        pred = lambda pos: 'jump' in map[pos]['actions']
        field = map.view_field(self.pos, self.actor_angle,
                                    c_angle, radius, pred)
        if char.pos in field:
            return True
        return False

    @property
    def face_to_player(self):
        if self.manager.player.pos == self.angle_to_pos(0):
            return True
        return False

    @action('die')
    def do_die(self):
        actor = self.actor
        ds = S.ch_anim['death_speed']
        dr = (S.ch_anim['forward_death_range'] if self.fall_forward
                                else S.ch_anim['backward_death_range'])
        anim_interval = actor.actorInterval(
            'anim', playRate=ds,
            startFrame=dr[0], endFrame=dr[1]
        )
        anim_interval.start()
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 0))
        yield interval
        anim_interval.finish()
        self.must_die = False
        self.dead = True
        yield wait(.5)

class Body(object):

    def __init__(self, npc, manager):
        self.npc = npc
        actor = npc.actor
        self.manager = manager
        map = manager.map

        pos = npc.angle_to_pos(0 if npc.fall_forward else 180)
        if map.check_square(npc.pos, pos, npc.walk_pred):
            second_pos = pos
        else:
            for n, info in manager.map.neighbors(npc.pos, True):
                if map.check_square(npc.pos, n, npc.walk_pred):
                    second_pos = n
                    break
            else:
                # lucky player
                npc.node.removeNode() # doesn't work in multithreading mode
                return
        self.poses = (npc.pos, second_pos) # order is important
        actor.pose('anim', S.npc['body_frame'])
        bs = S.npc['body_shift']
        actor.setHpr(-90, 0, 0)
        actor.setX(bs)
        angle = degrees(atan2(second_pos[1] - npc.pos[1],
                              second_pos[0] - npc.pos[0]))
        npc.node.setHpr(angle, 0, 0)
        self.show()

    @property
    def poses(self):
        return getattr(self, '_poses', None)

    @poses.setter
    def poses(self, value):
        assert type(value) is tuple
        for pos in value:
            assert pos in self.manager.map
        if hasattr(self, '_poses'):
            del self.manager.bodies[self._poses[0]]
            del self.manager.bodies[self._poses[1]]
        self._poses = value
        self.manager.bodies[self._poses[0]] = self
        self.manager.bodies[self._poses[1]] = self

    def hide(self, start=True):
        ds = S.ch_anim['death_speed']
        interval = LerpColorScaleInterval(self.npc.actor, 1 / ds / 7,
                                                        (1, 1, 1, 0))
        if not start:
            return interval
        interval.start()

    def show(self):
        ds = S.ch_anim['death_speed']
        interval = LerpColorScaleInterval(self.npc.actor, 1 / ds / 7,
                                                        (1, 1, 1, 1))
        interval.start()

    def get_poses(self, first_pos=None, angle=None):
        main_node = self.manager.main_node
        if first_pos is None:
            _pos = self.npc.node.getPos(main_node)
            first_pos = int(round(_pos[0])), int(round(_pos[1]))
        if angle is None:
            angle = self.npc.node.getHpr(main_node)[0]
        angle = int(round(angle)) % 360
        angle = angle if angle <= 180 else angle - 360
        diff = self.npc.reverse_angle_table[angle]
        second_pos = (int(round(first_pos[0] + diff[0])),
                      int(round(first_pos[1] - diff[1])))
        return (first_pos, second_pos)

    def check_poses(self, first_pos, angle):
        for pos in self.get_poses(first_pos, angle):
            if pos in self.poses:
                continue
            if not self.npc.walk_pred(pos):
                return False
        return True

    def update_poses(self):
        self.poses = self.get_poses()

    def bind(self, player):
        node = self.npc.node
        pos = player.angle_to_pos(0)
        node.setPos(pos[0], pos[1], 0)
        node.setHpr(player.actor_angle, 0, 0)
        node.wrtReparentTo(player.actor)
        self.show()

    def unbind(self):
        node = self.npc.node
        poses = self.get_poses()
        node.wrtReparentTo(self.manager.main_node)
        self.poses = poses
        node.setPos(poses[0][0], poses[0][1], 0)
        self.show()