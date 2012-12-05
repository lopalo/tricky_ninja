from collections import deque
from math import cos, sin, radians, atan2, degrees, hypot
from panda3d.core import *
from direct.interval.LerpInterval import LerpPosInterval
from direct.interval.ActorInterval import ActorInterval
from direct.actor.Actor import Actor

from character.char import Character
from character.player import Player
from character.action import action, wait


class NPC(Character):

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
        actor.setTransparency(False)
        actor.setScale(S.model_size(self.model))
        actor.setTexture(loader.loadTexture(
                            S.texture(texture)), 1)
        self.init_position = self.pos = route[0]
        self.node.setPos(self.pos[0], self.pos[1], 0)
        actor.pose('anim', S.npc['idle_frame'])
        actor.setBlend(frameBlend=True)
        if S.graphics['enable_cartoon']:
            actor.setAttrib(LightRampAttrib.makeSingleThreshold(0.5, 0.4))
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
            del self.manager.npcs[self._pos] #FIXME: KeyError
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
            return
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
            return
        return path[0]

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
        if self.must_die:
            self._start_action('die')
            return
        self._start_action(action)

    def in_view_field(self, char):
        assert isinstance(char, Character)
        map = self.manager.map
        radius, c_angle = self.view_radius, self.view_angle
        pred = lambda pos: 'see' in map[pos]['actions']
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

    @action
    def do_die(self):
        anim_interval = yield self._falling()
        anim_interval.finish()
        self.must_die = False
        self.dead = True
        yield wait(.5)
