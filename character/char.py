from direct.interval.LerpInterval import (
    LerpPosInterval,
    LerpHprInterval,
    LerpColorScaleInterval
)
from direct.interval.ActorInterval import ActorInterval
from character.action import action, wait, ret


class Character(object):
    model = 'ninja'

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

    def _start_action(self, name):
        getattr(self, 'do_' + name)()

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

    def _rotate_to(self, to_pos=None, angle=None, speed=None):
        assert to_pos is not None or angle is not None
        if angle is None:
            shift = to_pos[1] - self.pos[1], to_pos[0] - self.pos[0]
            angle = (self.angle_table[shift] + 180) % 360
        c_angle = self.actor.getHpr()[0] % 360
        d_angle = angle - c_angle
        sp = speed or self.speed
        if d_angle != 0:
            if abs(d_angle) > 180:
                angle = angle - 360 if d_angle > 0 else angle + 360
            dur = float(abs(angle - c_angle)) / 360 / sp * 2
            interval = LerpHprInterval(self.actor, dur, (angle, 0, 0),
                                                    (c_angle, 0, 0))
            yield interval

    @action
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
            next_pos = self.get_next_pos()
            if self.must_die or next_pos is None:
                break
            yield self._rotate_to(next_pos)

            if not map.check_square(self.pos, next_pos, self.walk_pred):
                break
            if self is self.manager.player and self.get_next_pos() is None:
                break
            shift = next_pos[1] - self.pos[1], next_pos[0] - self.pos[0]
            dur = 1.4 / sp if all(shift) else 1.0 / sp
            interval = LerpPosInterval(self.node, dur, next_pos + (0,))
            map.block(next_pos)
            self.walking = True
            yield interval
            self.pos = next_pos
            map.unblock(self.pos)
            self.walking = False
        anim.pose(self.idle_frame)

    @action
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

    def _falling(self):
        actor = self.actor
        ds = S.ch_anim['death_speed']
        dr = (S.ch_anim['forward_death_range'] if self.fall_forward
                                else S.ch_anim['backward_death_range'])
        anim_interval = actor.actorInterval(
            'anim', playRate=ds,
            startFrame=dr[0], endFrame=dr[1]
        )
        anim_interval.start()
        actor.setTransparency(True)
        interval = LerpColorScaleInterval(actor, 1 / ds / 7, (1, 1, 1, 0))
        yield interval
        yield ret(anim_interval)
