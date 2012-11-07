from math import hypot, sin, radians
from random import choice
from collections import defaultdict, deque

from direct.filter.CommonFilters import CommonFilters
from panda3d.core import *

from map_model.map import Map
from map_builder import MapBuilder
from character.player import Player
from character.npc import NPC
from character.body import Body


class Manager(object):

    def __init__(self, map_name):
        self.main_node = render.attachNewNode('main_node')
        self.blocked_squares = set()
        self.bodies = {}
        self.map = Map(map_name)
        self.map_builder = MapBuilder(self.map, self.main_node)
        self.map_builder.build()
        self.player = Player(self, self.map.start_pos)
        self.set_npcs()
        self.setup_graphics()

        if S.show_view_field:
            self.view_fields = defaultdict(set)
            taskMgr.doMethodLater(1, self.update_view_fields, 'fields')
        if S.show_pathes:
            self.pathes = defaultdict(set)
            taskMgr.doMethodLater(1, self.update_pathes, 'pathes')

    def set_npcs(self):
        self.npcs = {}
        for data in self.map.npcs:
            for _ in range(data['count']):
                _data = data.copy()
                route = deque(self.map.routes[data['route']])
                free = [i for i in route if i not in self.npcs]
                assert free, 'all postions are occupated'
                pos = choice(free)
                while pos != route[0]:
                    route.rotate(1)
                _data['route'] = route
                NPC(self, **_data).dead = True

    def is_available(self, pos):
        return (pos in self.map and
                (pos != self.player.pos or self.player.walking) and
                (pos not in self.npcs or self.npcs[pos].walking) and
                pos not in self.bodies)

    def __call__(self, task):
        self.player.update_action()
        for npc in tuple(self.npcs.values()):
            if not npc and npc.action is None:
                del self.npcs[npc._pos]
                Body(npc, self)
                continue
            npc.update_action()
        return task.cont

    def alert(self, pos, target_pos=None):
        for npc in self.npcs.values():
            if not npc:
                continue
            length = hypot(npc.pos[0] - pos[0], npc.pos[1] - pos[1])
            if length <= S.npc['alert_radius']:
                npc.target = target_pos or self.player
                npc.speed = S.npc['excited_speed']
                npc.view_radius = S.npc['excited_view_radius']
                npc.view_angle = S.npc['excited_view_angle']

    def setup_graphics(self):
        angle = self.map.hour * 15 - 90
        light_factor = max(sin(radians(angle)), 0)
        mnode = self.main_node
        alight = AmbientLight('alight')
        color = S.graphics['ambient_light_color'] + [light_factor]
        alight.setColor(VBase4(*color))
        alnp = mnode.attachNewNode(alight)
        mnode.setLight(alnp)

        dlight = DirectionalLight('dlight')
        color = S.graphics['light_color'] + [light_factor]
        dlight.setColor(VBase4(*color))
        dlnp = mnode.attachNewNode(dlight)
        dlnp.setHpr(0, -angle, 0)
        mnode.setLight(dlnp)

        if S.graphics['enable_shadows']:
            self.main_node.setShaderAuto() # doesn't work in multithreading mode
            lens = OrthographicLens()
            lens.setFilmSize(30, 30)
            lens.setNearFar(-1000, 1000)
            dlight.setLens(lens)
            ss = S.graphics['shadow_size']
            dlight.setShadowCaster(True, ss, ss)
            dlnp.reparentTo(self.player.node)
        if S.graphics['enable_cartoon']:
            self.main_node.setShaderAuto() # doesn't work in multithreading mode
            mnode.setAttrib(LightRampAttrib.makeSingleThreshold(0.5, 0.4))
            self.filters = CommonFilters(base.win, base.cam)
            self.filters.setCartoonInk(1)


    def update_view_fields(self, task):
        """ It is a very expensive funciton. Use only for debugging """
        for npc in self.npcs.values():
            key = id(npc)
            for marker in self.view_fields[key]:
                marker.removeNode()
            del self.view_fields[key]
            radius, c_angle = npc.view_radius, npc.view_angle
            angle = int(npc.actor.getHpr()[0] - 90) % 360
            pred = lambda pos: 'jump' in self.map[pos]['actions']
            field = self.map.view_field(npc.pos, angle,
                                        c_angle, radius, pred)
            for pos in field:
                marker = loader.loadModel(S.model('plane'))
                marker.setHpr(0, -90, 0)
                marker.reparentTo(self.main_node)
                marker.setPos(pos[0], pos[1], 0.1)
                self.view_fields[key].add(marker)
        return task.again

    def update_pathes(self, task):
        """ It is a very expensive funciton. Use only for debugging """

        map = self.map
        for npc in self.npcs.values():
            key = id(npc)
            for marker in self.pathes[key]:
                marker.removeNode()
            del self.pathes[key]
            target = npc.target
            end_pos = target if isinstance(target, tuple) else target.pos
            pred = lambda pos: ('walk' in map[pos]['actions'] and
                                map.is_available(pos) and
                                (pos not in self.npcs or
                                self.npcs[pos].walking) and
                                pos not in self.bodies)
            path = map.get_path(npc.pos, end_pos, pred)
            if path is None:
                continue

            for pos in path:
                marker = loader.loadModel(S.model('plane'))
                marker.setHpr(0, -90, 0)
                marker.reparentTo(self.main_node)
                marker.setPos(pos[0], pos[1], 0.1)
                self.pathes[key].add(marker)
        return task.again