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
        return ('walk' in map[pos]['actions'] and
                map.is_available(pos) and
                self.manager.is_available(pos))

    @action('walk')
    def do_walk(self):
        yield wait(.05)
        map = self.manager.map
        actor = self.actor
        anim = actor.getAnimControl('anim')
        sp = float(self.speed)
        anim.setPlayRate(sp / 2)
        wr = S.ch_anim['walk_range']
        anim.loop(True, wr[0], wr[1])
        while True:
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
            dur = 1.4 / sp if all(shift) else 1.0 / sp
            mid_pos = (float(self.pos[0] + next_pos[0]) / 2,
                       float(self.pos[1] + next_pos[1]) / 2)
            interval = LerpPosInterval(self.node, dur / 2, mid_pos + (0,))
            map.block(next_pos)
            yield interval
            self.pos = next_pos
            map.unblock(self.pos)
            interval = LerpPosInterval(self.node, dur / 2, next_pos + (0,))
            yield interval
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
        angle = int((actor.getHpr()[0] % 360) - 90)
        angle = angle if angle <= 180 else angle - 360
        diff = self.reverse_angle_table[angle]
        target_coord = self.pos[0] + diff[0], self.pos[1] - diff[1]
        if target_coord in self.manager.npcs:
            self.manager.npcs[target_coord].kill()
        elif self.manager.player.pos == target_coord:
            self.manager.player.kill()
        interval = actor.actorInterval(
            'anim',
            playRate=self.post_hit_speed,
            startFrame=self.post_hit_range[0],
            endFrame=self.post_hit_range[1]
        )
        yield interval
        actor.pose('anim', self.idle_frame)

    @property
    def must_die_event(self):
        return 'die:' + str(id(self))

    def kill(self):
        if not self:
            return
        self.must_die = True
        messenger.send(self.must_die_event)


class Player(Character):
    actions = Character.actions.copy()
    #TODO: implement corpse moving

    def __init__(self, manager, pos):
        super(Player, self).__init__(manager)

        self.speed = S.player['speed']
        self.idle_frame = S.player['idle_frame']
        self.hit_range = S.pl_anim['hit_range']
        self.hit_speed = S.pl_anim['hit_speed']
        self.post_hit_range = S.pl_anim['post_hit_range']
        self.post_hit_speed = S.pl_anim['post_hit_speed']

        self.move_direction = [0, 0] #[forward, right]
        self.actor = actor = Actor(S.model(S.player['model']),
                                    {'anim': S.model(S.player['model'])})
        self.actor.reparentTo(self.node)
        actor.setScale(S.model_size(S.player['model']))
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
        def up():
            self.move_direction[0] = 1
            self.update_action('walk')
        def up_up():
            self.move_direction[0] = 0
        base.accept('arrow_up', up)
        base.accept('arrow_up-up', up_up)
        def down():
            self.move_direction[0] = -1
            self.update_action('walk')
        def down_up():
            self.move_direction[0] = 0
        base.accept('arrow_down', down)
        base.accept('arrow_down-up', down_up)
        def right():
            self.move_direction[1] = 1
            self.update_action('walk')
        def right_up():
            self.move_direction[1] = 0
        base.accept('arrow_right', right)
        base.accept('arrow_right-up', right_up)
        def left():
            self.move_direction[1] = -1
            self.update_action('walk')
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

        if self.walk_pred(new_pos):
            if not map.is_corner(pos, new_pos):
                return new_pos, True
            elif map.is_free_corner(pos, new_pos, self.walk_pred):
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
        actor = self.actor
        wr, ds = S.ch_anim['death_range'], S.ch_anim['death_speed']
        interval = actor.actorInterval(
            'anim', playRate=ds,
            startFrame=wr[0], endFrame=wr[1]
        )
        interval.start()
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 0))
        yield interval
        yield wait(1)
        init_pos = tuple(self.init_position)
        if (not self.manager.map.is_available(init_pos) or
            not self.manager.is_available(init_pos)):
                return
        self.must_die = False
        self.dead = False
        self.pos = init_pos
        self.node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', self.idle_frame)
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 1))
        yield interval


class NPC(Character):
    actions = Character.actions.copy()

    def __init__(self, manager, model_name, texture, route, **spam):
        super(NPC, self).__init__(manager)

        self.view_radius = S.npc['normal_view_radius']
        self.view_angle = S.npc['normal_view_angle']
        self.speed = S.npc['speed']
        self.idle_frame = S.npc['idle_frame']
        self.hit_range = S.npc_anim['hit_range']
        self.hit_speed = S.npc_anim['hit_speed']
        self.post_hit_range = S.npc_anim['post_hit_range']
        self.post_hit_speed = S.npc_anim['post_hit_speed']

        self.actor = actor = Actor(S.model(model_name),
                                    {'anim': S.model(model_name)})
        self.actor.reparentTo(self.node)
        actor.setTransparency(True)
        actor.setScale(S.model_size(model_name))
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
        map = self.manager.map
        target = self.target
        end_pos = target if isinstance(target, tuple) else target.pos
        pred = lambda pos: ('walk' in map[pos]['actions'] and
                            map.is_available(pos) and
                            pos not in self.manager.npcs)
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
                if self.face_to_player:
                    return 'hit'
                else:
                    return 'walk'
            else:
                return 'walk'
        else:
            #TODO: check if corpse is in view_field
            if self.in_view_field(player):
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
        angle = int(self.actor.getHpr()[0] - 90) % 360
        pred = lambda pos: 'jump' in map[pos]['actions']
        field = map.view_field(self.pos, angle,
                                    c_angle, radius, pred)
        if char.pos in field:
            return True
        return False

    @property
    def face_to_player(self):
        angle = int(self.actor.getHpr()[0] - 90) % 360
        angle = angle if angle <= 180 else angle - 360
        if angle not in self.reverse_angle_table:
            return False
        diff = self.reverse_angle_table[angle]
        pos = self.pos[0] + diff[0], self.pos[1] - diff[1]
        if self.manager.player.pos == pos:
            return True
        return False

    @action('die')
    def do_die(self):
        actor = self.actor
        wr, ds = S.ch_anim['death_range'], S.ch_anim['death_speed']
        anim_interval = actor.actorInterval(
            'anim', playRate=ds,
            startFrame=wr[0], endFrame=wr[1]
        )
        anim_interval.start()
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 0))
        yield interval
        anim_interval.finish()
        self.must_die = False
        self.dead = True

class Body(object):

    def __init__(self, npc, manager):
        self.npc = npc
        self.actor = actor = npc.actor
        self.manager = manager
        for n, info in manager.map.neighbors(npc.pos, True):
            if npc.walk_pred(n):
                second_pos = n
                #TODO: implement model rotation considering Y shift
                break
        else:
            # lucky player
            actor.delete()
            return
        self.poses = frozenset((npc.pos, second_pos))
        actor.pose('anim', S.npc['body_frame'])
        ds, bs = S.ch_anim['death_speed'], S.npc['body_shift']
        actor.setY(actor, bs)
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 1))
        interval.start()

    @property
    def poses(self):
        return getattr(self, '_poses', None)

    @poses.setter
    def poses(self, value):
        assert type(value) is frozenset
        for pos in value:
            assert pos in self.manager.map
        if hasattr(self, '_poses'):
            del self.manager.npcs[self._poses]
        self._poses = value
        self.manager.bodies[self._poses] = self

    def bind(self, player):
        pass