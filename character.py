from functools import wraps
from collections import deque
from math import cos, sin, radians, atan2, degrees, hypot
from types import GeneratorType
from direct.interval.LerpInterval import (LerpPosInterval,
                                LerpHprInterval, LerpNodePathInterval)
from direct.interval.ProjectileInterval import ProjectileInterval
from direct.interval.ActorInterval import ActorInterval
from direct.actor.Actor import Actor

_actions = {}

def action(name):
    assert name not in _actions
    def wrapper(func):
        @wraps(func)
        def wrap(char, *args, **kwargs):
            assert isinstance(char, Character)
            char.action = name
            gen = func(char, *args, **kwargs)
            assert isinstance(gen, GeneratorType)
            _runner(char, gen, None)
        _actions[name] = wrap
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


class Character:
    actions = _actions

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

    def __init__(self, manager):
        self.action = None
        self.must_die = False
        self.move_direction = [0, 0] #[forward, right]
        self.manager = manager
        self.node = node = render.attachNewNode(str(id(self)))
        self.actor = actor = Actor(S.model(S.player['model']),
                                    {'anim': S.model(S.player['model'])})
        self.actor.reparentTo(node)
        actor.setScale(S.model_size(S.player['model']))
        self.pos = tuple(S.player['init_position'])
        node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', S.player['idle_frame'])
        node.reparentTo(manager.main_node)
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

    def update_action(self, action=None):
        #calls in every frame and by some
        #events('arrows'...)

        assert action in self.actions or action == None
        if self.action is not None:
            return
        if self.must_die:
            self.do_die()
        if action is not None:
            self.actions[action](self)

    def get_next_pos(self):
        #different for NPC and Player
        #for Player it should read direction that was set by arrow events
        #for NPC it should be a next position of path
        move_dir = tuple(self.move_direction)
        pos = self.pos
        if move_dir == (0, 0):
            return
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
        nbs = dict(self.manager.map.neighbors(pos, True, True))
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
                    if direction not in nbs:
                        return
                    break
                directions.rotate(1)
            shift = self.manager.map._neighbors[direction]
        return (pos[0] + shift[0], pos[1] + shift[1])

    @action('walk')
    def do_walk(self):
        yield wait(.05)
        actor = self.actor
        anim = actor.getAnimControl('anim')
        sp = float(S.player['speed'])
        anim.setPlayRate(sp / 2)
        wr = S.player['walk_range']
        anim.loop(True, wr[0], wr[1])
        while True:
            next_pos = self.get_next_pos()
            if self.must_die or next_pos is None:
                break
            shift = next_pos[1] - self.pos[1], next_pos[0] - self.pos[0]
            angle = (self.angle_table[shift] + 180) % 360
            c_angle = actor.getHpr()[0] % 360
            d_angle = angle - c_angle
            if d_angle != 0:
                if abs(d_angle) > 180:
                    angle = angle - 360 if d_angle > 0 else angle + 360
                dur = float(abs(angle - c_angle)) / 360 / sp
                interval = LerpHprInterval(actor, dur, (angle, 0, 0),
                                                       (c_angle, 0, 0))
                yield interval
            dur = 1.4 / sp if all(shift) else 1.0 / sp
            interval = LerpPosInterval(self.node, dur, next_pos + (0,))
            yield interval
            self.pos = next_pos
        anim.pose(S.player['idle_frame'])

    @property
    def must_die_event(self):
        return 'die:' + str(id(self))

    def kill(self):
        self.must_die = True
        messenger.send(self.must_die_event)
        #do something addition actions

    @action('jump')
    def do_jump(self):
        def pred(info):
            return True #remove later
            return 'jump' in info['actions']
        field = self.manager.map.get_field(self.pos, 2, pred)
        next(field)
        field = deque(sorted(sum(field, [])))
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
        sp = float(S.player['speed'])
        v = pos[0] - self.pos[0], pos[1] - self.pos[1]
        dist = float(hypot(v[0], v[1]))
        angle = (degrees(atan2(v[1], v[0])) + 90) % 360
        c_angle = actor.getHpr()[0] % 360
        d_angle = angle - c_angle
        if d_angle != 0:
            if abs(d_angle) > 180:
                angle = angle - 360 if d_angle > 0 else angle + 360
            dur = float(abs(angle - c_angle)) / 360 / sp
            interval = LerpHprInterval(actor, dur, (angle, 0, 0),
                                                    (c_angle, 0, 0))
            anim = actor.getAnimControl('anim')
            anim.setPlayRate(sp / 2)
            wr = S.player['walk_range']
            anim.loop(True, wr[0], wr[1])
            yield interval
        wr = S.player['pre_jump_range']
        interval = actor.actorInterval(
            'anim',
            playRate=S.player['pre_jump_speed'],
            startFrame=wr[0], endFrame=wr[1]
        )
        yield interval
        interval = ProjectileInterval(actor, (0, 0, 0),
                    (0, 0, 0), 1, gravityMult=S.player['jump_height'])
        interval.start()
        interval = LerpPosInterval(self.node, 1, pos + (0,))
        yield interval
        wr = S.player['post_jump_range']
        interval = actor.actorInterval(
            'anim',
            playRate=S.player['post_jump_speed'],
            startFrame=wr[0], endFrame=wr[1]
        )
        yield interval
        self.pos = pos
        yield wait(0.1)
        actor.pose('anim', S.player['idle_frame'])


