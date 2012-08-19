from math import hypot
from random import choice
from collections import defaultdict, deque
from map_model.map import Map
from map_builder import MapBuilder
import character


class Manager(object):

    def __init__(self, map_name):
        self.main_node = render.attachNewNode('main_node')
        self.blocked_squares = set()
        self.bodies = {}
        self.map = Map(map_name)
        self.map_builder = MapBuilder(self.map, self.main_node)
        self.map_builder.build()
        self.player = character.Player(self, self.map.start_pos)
        self.set_npcs()
        if S.show_view_field:
            self.view_fields = defaultdict(set)
            taskMgr.doMethodLater(1, self.update_view_fields, 'fields')

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
                character.NPC(self, **_data)

    def _body_occupied(self, pos):
        for poses in self.bodies:
            if pos in poses:
                return True
        return False

    def is_available(self, pos):
        return (pos in self.map and
                (pos != self.player.pos or self.player.walking) and
                (pos not in self.npcs or self.npcs[pos].walking) and
                not self._body_occupied(pos))

    def __call__(self, task):
        self.player.update_action()
        for npc in tuple(self.npcs.values()):
            if not npc and npc.action is None:
                del self.npcs[npc._pos]
                body = character.Body(npc, self)
                if body.poses is None:
                    continue
                self.bodies[body._poses] = body
                continue
            npc.update_action()
        return task.cont

    def alert(self, pos, target_pos=None):
        for npc in self.npcs.values():
            if not npc:
                continue
            length = hypot(npc.pos[0] - pos[0], npc.pos[1] - pos[1])
            if length <= S.alert_radius:
                npc.target = target_pos or self.player
                npc.speed = S.npc['excited_speed']
                npc.view_radius = S.npc['excited_view_radius']
                npc.view_angle = S.npc['excited_view_angle']


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
