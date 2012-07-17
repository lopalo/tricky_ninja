from math import hypot
from collections import defaultdict
import map
from map_builder import MapBuilder
import character


class Manager(object):


    def __init__(self, map_name):
        self.main_node = render.attachNewNode('main_node')
        self.blocked_squares = set()
        self.map = map.Map(map_name)
        self.map_builder = MapBuilder(self.map, self.main_node)
        self.map_builder.build()
        self.player = character.Player(self)
        self.set_npcs()
        if S.show_view_field:
            self.view_fields = defaultdict(set)
            taskMgr.doMethodLater(1, self.update_view_fields, 'fields')


    def set_npcs(self):
        self.npcs = {}
        #TODO: change this shit later
        pos, model, texture = (3, 3), 'ninja', 'nskinbr'
        route = ((0, 13), (17, 4))
        self.npcs[pos] = character.NPC(self, model, texture, pos, route)
        pos = (5, 5)
        route = ((0, 13), (21, 8))
        self.npcs[pos] = character.NPC(self, model, texture, pos, route)

    def is_available(self, pos):
        return (pos in self.map and
                pos != self.player.pos and
                pos not in self.npcs)

    def __call__(self, task):
        self.player.update_action()
        for npc in tuple(self.npcs.values()):
            if not npc:
                continue
            npc.update_action()
        return task.cont

    def alert(self, pos):
        for npc in self.npcs.values():
            if not npc:
                continue
            length = hypot(npc.pos[0] - pos[0], npc.pos[1] - pos[1])
            if length <= S.alert_radius:
                #TODO: change speed of walk
                npc.target = self.player
                npc.view_radius = S.npc['excited_view_radius']
                npc.view_angle = S.npc['excited_view_angle']


    def update_view_fields(self, task):
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
