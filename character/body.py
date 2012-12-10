from math import cos, sin, radians, atan2, degrees, hypot
from direct.interval.LerpInterval import LerpPosInterval, LerpColorScaleInterval


class Body(object):

    def __init__(self, npc, manager):
        self.lock = False
        self.npc = npc
        actor = npc.actor
        self.manager = manager
        map = manager.map

        pos = npc.angle_to_pos(0 if npc.fall_forward else 180)
        if map.check_square(npc.pos, pos, npc.walk_pred):
            second_pos = pos
        else:
            for n, info in manager.map.neighbors(npc.pos, True):
                if map.check_square(npc.pos, n, npc.walk_pred):
                    second_pos = n
                    break
            else:
                # lucky player
                npc.node.removeNode() # doesn't work in multithreading mode
                return
        self.poses = (npc.pos, second_pos) # order is important
        actor.pose('anim', S.npc['body_frame'])
        bs = S.npc['body_shift']
        actor.setHpr(-90, 0, 0)
        actor.setX(bs)
        angle = degrees(atan2(second_pos[1] - npc.pos[1],
                              second_pos[0] - npc.pos[0]))
        npc.node.setHpr(angle, 0, 0)
        self.show()

    def __nonzero__(self):
        return self.npc.dead

    @property
    def poses(self):
        return getattr(self, '_poses', None)

    @poses.setter
    def poses(self, value):
        assert type(value) is tuple
        for pos in value:
            assert pos in self.manager.map
        if hasattr(self, '_poses'):
            del self.manager.bodies[self._poses[0]]
            del self.manager.bodies[self._poses[1]]
        self._poses = value
        self.manager.bodies[self._poses[0]] = self
        self.manager.bodies[self._poses[1]] = self

    def hide(self, start=True):
        self.npc.actor.setTransparency(True)
        ds = S.ch_anim['death_speed']
        interval = LerpColorScaleInterval(self.npc.actor, 1 / ds / 7,
                                                        (1, 1, 1, 0))
        if not start:
            return interval
        interval.start()

    def show(self):
        ds = S.ch_anim['death_speed']
        interval = LerpColorScaleInterval(self.npc.actor, 1 / ds / 7,
                                                        (1, 1, 1, 1))
        def callback():
            self.npc.actor.setTransparency(False)
        interval.setDoneEvent('body_showed')
        base.acceptOnce('body_showed', callback)
        interval.start()

    def get_poses(self, first_pos=None, angle=None):
        main_node = self.manager.main_node
        if first_pos is None:
            _pos = self.npc.node.getPos(main_node)
            first_pos = int(round(_pos[0])), int(round(_pos[1]))
        if angle is None:
            angle = self.npc.node.getHpr(main_node)[0]
        angle = int(round(angle)) % 360
        angle = angle if angle <= 180 else angle - 360
        diff = self.npc.reverse_angle_table[angle]
        second_pos = (int(round(first_pos[0] + diff[0])),
                      int(round(first_pos[1] - diff[1])))
        return (first_pos, second_pos)

    def check_poses(self, first_pos, angle):
        for pos in self.get_poses(first_pos, angle):
            if pos in self.poses:
                continue
            if not self.npc.walk_pred(pos):
                return False
        return True

    def update_poses(self):
        self.poses = self.get_poses()

    def bind(self, player):
        node = self.npc.node
        pos = player.angle_to_pos(0)
        node.setPos(pos[0], pos[1], 0)
        node.setHpr(player.actor_angle, 0, 0)
        node.wrtReparentTo(player.actor)
        self.update_poses()
        self.show()

    def unbind(self):
        node = self.npc.node
        poses = self.get_poses()
        node.wrtReparentTo(self.manager.main_node)
        self.poses = poses
        node.setPos(poses[0][0], poses[0][1], 0)
        self.show()

    def revive(self):
        del self.manager.bodies[self.poses[0]]
        del self.manager.bodies[self.poses[1]]
        pos = self.poses[0]
        npc = self.npc
        npc.pos = pos
        npc.node.setPos(pos[0], pos[1], 0)
        npc.actor.setX(0)
        npc.actor.pose('anim', S.npc['idle_frame'])
        npc.node.setH(0)
        npc.dead = False
        npc.target = npc.init_position
        self.show()
        self.lock = False