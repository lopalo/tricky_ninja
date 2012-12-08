from collections import deque
from math import cos, sin, radians, atan2, degrees, hypot
from panda3d.core import *
from direct.interval.LerpInterval import (
    LerpPosInterval,
    LerpColorScaleInterval
)
from direct.interval.ProjectileInterval import ProjectileInterval
from direct.interval.ActorInterval import ActorInterval
from direct.actor.Actor import Actor

from character.char import Character
from character.action import action, wait, events, ret


class Player(Character):

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
        actor.setTransparency(False)
        actor.setTexture(loader.loadTexture(
                            S.texture(S.player['texture'])), 1)
        self.pos = self.init_position = pos
        self.node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', self.idle_frame)
        actor.setBlend(frameBlend=True)
        self.set_camera()
        self.set_move_handlers()
        self.set_control()
        if S.graphics['enable_cartoon']:
            actor.setAttrib(LightRampAttrib.makeSingleThreshold(0.5, 0.4))

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        assert value in self.manager.map
        prev_pos = getattr(self, '_pos', None)
        self._pos = value
        self.manager.on_player_moved(prev_pos, value)

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
        key = S.control_keys['rotate_camera_counterclockwise']
        base.accept(key, incr_angle)
        base.accept(key + '-repeat', incr_angle)
        def decr_angle():
            self.cam_angle -= S.camera['vertical_angle_step']
            recalc()
        key = S.control_keys['rotate_camera_clockwise']
        base.accept(key, decr_angle)
        base.accept(key + '-repeat', decr_angle)
        def incr_dist():
            self.cam_distance += S.camera['distance_step']
            recalc()
        key = S.control_keys['increase_camera_distance']
        base.accept(key, incr_dist)
        base.accept(key + '-repeat', incr_dist)
        def decr_dist():
            self.cam_distance -= S.camera['distance_step']
            recalc()
        key = S.control_keys['decrease_camera_distance']
        base.accept(key, decr_dist)
        base.accept(key + '-repeat', decr_dist)
        recalc()

    def set_move_handlers(self):
        def common_handler():
            if self.captured_body:
                messenger.send(self.continue_move_body_event)
            else:
                self.update_action('walk')
        def forward():
            self.move_direction[0] = 1
            common_handler()
        def forward_up():
            self.move_direction[0] = 0
        key = S.control_keys['move_forward']
        base.accept(key, forward)
        base.accept(key + '-up', forward_up)
        def backward():
            self.move_direction[0] = -1
            common_handler()
        def backward_up():
            self.move_direction[0] = 0
        key = S.control_keys['move_backward']
        base.accept(key, backward)
        base.accept(key + '-up', backward_up)
        def right():
            self.move_direction[1] = 1
            common_handler()
        def right_up():
            self.move_direction[1] = 0
        key = S.control_keys['move_right']
        base.accept(key, right)
        base.accept(key + '-up', right_up)
        def left():
            self.move_direction[1] = -1
            common_handler()
        def left_up():
            self.move_direction[1] = 0
        key = S.control_keys['move_left']
        base.accept(key, left)
        base.accept(key + '-up', left_up)

    def remove_move_handlers(self):
        key = S.control_keys['move_forward']
        base.ignore(key)
        base.ignore(key + '-up')
        key = S.control_keys['move_backward']
        base.ignore(key)
        base.ignore(key + '-up')
        key = S.control_keys['move_left']
        base.ignore(key)
        base.ignore(key + '-up')
        key = S.control_keys['move_right']
        base.ignore(key)
        base.ignore(key + '-up')

    def set_control(self):
        def start_jump():
            self.update_action('jump')
        base.accept(S.control_keys['jump'], start_jump)
        base.accept(S.control_keys['kill_self'], self.kill)
        def hit_down():
            self.update_action('hit')
        base.accept(S.control_keys['hit'], hit_down)
        def start_move_body():
            self.captured_body = True
            self.update_action('move_body')
        base.accept(S.control_keys['move_body'], start_move_body)
        def finish_move_body():
            self.captured_body = False
            messenger.send(self.release_body_event)
        base.accept(S.control_keys['move_body'] + '-up', finish_move_body)

    def kill(self, hit_angle=0):
        if not self:
            return
        super(Player, self).kill(hit_angle)
        messenger.send(self.must_die_event)

    def update_action(self, action=None):
        #calls in every frame and by some
        #events

        if not self:
            return
        if self.action is not None:
            return
        if self.must_die:
            self._start_action('die')
            return
        if action is not None:
            self._start_action(action)
        elif tuple(self.move_direction) != (0, 0):
            self._start_action('walk')

    def get_next_pos(self):
        move_dir = tuple(self.move_direction)
        map = self.manager.map
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
                    break
                directions.rotate(1)
            shift = map._neighbors[direction]
        new_pos = pos[0] + shift[0], pos[1] + shift[1]
        return new_pos

    @action
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
            finish_event = S.control_keys['jump'] + '-up'
            left_key = S.control_keys['move_left']
            right_key = S.control_keys['move_right']
            val = yield events(left_key, left_key + '-repeat',
                               right_key, right_key + '-repeat',
                               finish_event, self.must_die_event)
            if val in (self.must_die_event, finish_event):
                break
            elif val in (left_key, left_key + '-repeat'):
                field.rotate(1)
            elif val in (right_key, right_key + '-repeat'):
                field.rotate(-1)
            else:
                raise Exception('Unknown event "{}"'.format(val))
        self.set_move_handlers()
        pointer.removeNode()
        if self.must_die:
            return
        actor = self.actor
        sp = float(self.speed)
        v = pos[0] - self.pos[0], pos[1] - self.pos[1]
        dist = float(hypot(v[0], v[1]))
        angle = (degrees(atan2(v[1], v[0])) + 90) % 360
        anim = actor.getAnimControl('anim')
        anim.setPlayRate(sp / 2)
        wr = S.ch_anim['walk_range']
        anim.loop(True, wr[0], wr[1])
        yield self._rotate_to(angle=angle)
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

    @action
    def do_die(self):
        self.dead = True
        self.must_die = False
        yield self._falling()
        yield wait(1)
        init_pos = self.init_position
        if (not self.manager.map.is_available(init_pos) or
            not self.manager.is_available(init_pos)):
                return # TODO: maybe delete player
        self.dead = False
        self.pos = init_pos
        self.node.setPos(self.pos[0], self.pos[1], 0)
        self.actor.pose('anim', self.idle_frame)
        ds = S.ch_anim['death_speed']
        interval = LerpColorScaleInterval(self.actor, 1 / ds / 7, (1, 1, 1, 1))
        yield interval
        self.actor.setTransparency(False)

    def _body_moving_step(self, body):
        sp = float(S.player['body_moving_speed'])
        map = self.manager.map
        next_pos = self.get_next_pos()
        if self.must_die or next_pos is None:
            yield ret(False)
        shift = next_pos[1] - self.pos[1], next_pos[0] - self.pos[0]
        # new body pos after rotation but berfore moving
        new_bpos = self.pos[0] - shift[1], self.pos[1] - shift[0]
        if body.poses[0] != new_bpos:
            bpath = map.get_radial_path(self.pos, body.poses[0],
                                        new_bpos, self.walk_pred, 2)
            if not bpath:
                yield ret(False)
            prev_bpos = body.poses[0]
            for cur_bpos in bpath:
                if not map.get_radial_path(self.pos,
                                           prev_bpos,
                                           cur_bpos,
                                           self.walk_pred,
                                           2):
                    break
                #cur_bpos is pos to which player should rotate
                yield self._rotate_to(cur_bpos, speed=sp)
                prev_bpos = cur_bpos
                body.update_poses()
            if cur_bpos != new_bpos:
                yield ret(False)
        if not map.check_square(self.pos, next_pos, self.walk_pred):
            yield ret(False)
        if self.get_next_pos() is None:
            yield ret(False)
        dur = 1.4 / sp if all(shift) else 1.0 / sp
        interval = LerpPosInterval(self.node, dur, next_pos + (0,))
        map.block(next_pos)
        self.walking = True
        yield interval
        self.pos = next_pos
        map.unblock(self.pos)
        self.walking = False
        body.update_poses()

    @action
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
            playRate=S.ch_anim['pick_up_speed'],
            startFrame=S.ch_anim['pick_up_range'][0],
            endFrame=S.ch_anim['pick_up_range'][1]
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
                ok = yield self._body_moving_step(body)
                if type(ok) is bool and not ok:
                    break
            anim.pose(S.player['body_captured_frame'])
        yield body.hide(False)
        body.unbind()