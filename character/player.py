from collections import deque
from math import cos, sin, radians, atan2, degrees, hypot
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

    def kill(self, hit_angle=0):
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

    @action('die')
    def do_die(self):
        self.dead = True
        self.must_die = False
        yield self._falling()
        yield wait(1)
        init_pos = tuple(self.init_position)
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
                ok = yield self._body_moving_step(body)
                if type(ok) is bool and not ok:
                    break
            anim.pose(S.player['body_captured_frame'])
        yield body.hide(False)
        body.unbind()