from math import hypot, sin, radians
from random import choice
from collections import defaultdict, deque

from panda3d.core import *

from map_model.map import Map
from map_builder import MapBuilder
from character.player import Player
from character.npc import NPC, TargetNPC
from character.body import Body


class Manager(object):
    #TODO: optimization (LOD, ...)

    #TODO: clear loaded parts of map textures

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
                NPC(self, **_data)#.dead = True # for debugging
        data = self.map.target_npc.copy()
        route = deque(self.map.routes[data['route']])
        data['route'] = route
        TargetNPC(self, **data)

    def is_available(self, pos):
        return (pos in self.map and
                (pos != self.player.pos or self.player.walking) and
                (pos not in self.npcs or self.npcs[pos].walking) and
                pos not in self.bodies)

    def __call__(self, task):
        self.player.update_action()
        for npc in tuple(self.npcs.values()):
            if not npc and npc.action is None:
                if isinstance(npc, TargetNPC):
                    print 'SUCCESS' #TODO: change to exit of manager
                del self.npcs[npc.pos]
                Body(npc, self)
                continue
            npc.update_action()
            if isinstance(npc, TargetNPC) and npc.pos == self.map.escape_position:
                print 'FAIL' #TODO: change to exit of manager
        return task.cont

    def on_player_moved(self, prev_pos, pos):
        map = self.map
        if prev_pos is None:
            prev_group = None
        elif map[prev_pos]['kind'] != 'model_field':
            prev_group = map[prev_pos]['ident']
        else:
            prev_group = map[prev_pos]['group']
        if map[pos]['kind'] != 'model_field':
            group = map[pos]['ident']
        else:
            group = map[pos]['group']
        if prev_group == group:
            return
        if prev_group is not None:
            for pos in map.groups[prev_group]:
                model = self.map_builder.get_model(pos)
                if model is None:
                    continue
                model.setAlphaScale(1)
        for pos in map.groups[group]:
            model = self.map_builder.get_model(pos)
            if model is None:
                continue
            model.setAlphaScale(S.graphics['transparency'])

    def alert(self, pos, target=None):
        for npc in self.npcs.values():
            if not npc:
                continue
            length = hypot(npc.pos[0] - pos[0], npc.pos[1] - pos[1])
            if length <= S.npc['alert_radius']:
                if isinstance(npc, TargetNPC):
                    npc.target = self.map.escape_position
                    npc.speed = S.target_npc['escape_speed']
                else:
                    npc.target = target or self.player
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
            # set for models separately
            self.main_node.setShaderAuto() # doesn't work in multithreading mode

    def update_view_fields(self, task):
        """ It is a very expensive funciton. Use only for debugging """
        for npc in self.npcs.values():
            key = id(npc)
            for marker in self.view_fields[key]:
                marker.removeNode()
            del self.view_fields[key]
            radius, c_angle = npc.view_radius, npc.view_angle
            angle = int(npc.actor.getHpr()[0] - 90) % 360
            pred = lambda pos: 'see' in self.map[pos]['actions']
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