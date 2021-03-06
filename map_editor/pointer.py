from panda3d.core import *

class Pointer:

    def __init__(self, editor):
        self.editor = editor
        self.prev_x = None
        self.map_pointer = None

        self.pointer = pointer = loader.loadModel(S.model('plane'))
        texture = loader.loadTexture(S.texture('red_pointer'))
        pointer.setTexture(texture)
        pointer.setTransparency(True)
        pointer.setHpr(0, -90, 0)
        pointer.reparentTo(render)
        pointer.setBin("fixed", 40)
        pointer.setDepthTest(False)
        pointer.setDepthWrite(False)

        self.plane = plane = Plane((0, 0, 0), (1, 1, 0), (1, 0, 0))

        base.accept(ES.control_keys['set_group_for_square'], self.on_left_click)
        base.accept(ES.control_keys['select_group_by_square'],
                                            self.on_right_click)

    @property
    def pos(self):
        return base.mouseWatcherNode.getMouse()

    @property
    def map_pos(self):
        pos = self.pointer.getPos()
        return int(pos[0]), int(pos[1])

    def on_left_click(self):
        map = self.editor.map
        if not self.map_pointer:
            return
        cur_g = self.editor.current_group
        if self.map_pos in map:
            map.groups[map[self.map_pos]['ident']].remove(self.map_pos)
        if cur_g is None:
            if self.map_pos in map:
                del map[self.map_pos]
        else:
            map[self.map_pos] = cur_g
            map.groups[cur_g['ident']].append(self.map_pos)
        self.editor.set_marker(self.map_pos)
        self.editor.map_builder.redraw_9_squares(self.map_pos, cur_g)

    def on_right_click(self):
        map = self.editor.map
        group_id = map[self.map_pos]['ident'] if self.map_pos in map else None
        self.editor.select_group(group_id)

    def update(self, task):
        if not base.mouseWatcherNode.hasMouse():
            return task.cont
        self._switch()
        self.prev_x = self.pos[0]
        if self.map_pointer:
            self._update_camera_position()
            self._update_map_cursor_position()
        return task.cont

    def _switch(self):
        prev_x = self.prev_x
        cur_x = self.pos[0]
        if (prev_x is None or prev_x < ES.border) and cur_x >= ES.border:
            props = WindowProperties()
            props.setCursorHidden(False)
            base.win.requestProperties(props)
            self.map_pointer = False
        elif (prev_x is None or prev_x > ES.border) and cur_x <= ES.border:
            props = WindowProperties()
            props.setCursorHidden(True)
            base.win.requestProperties(props)
            self.map_pointer = True

    def _update_camera_position(self):
        mborder = ES.pointer['move_camera_border']
        hstep = ES.camera['horizontal_move_step']
        cnode = self.editor.camera_node
        pos = self.pos
        if pos[0] < -(1 - mborder):
            cnode.setX(cnode, -hstep)
        if pos[0] > ES.border - mborder:
            cnode.setX(cnode, hstep)
        if pos[1] < -(1 - mborder):
            cnode.setY(cnode, -hstep)
        if pos[1] > (1 - mborder):
            cnode.setY(cnode, hstep)

    def _update_map_cursor_position(self):
        pos = Point3()
        near_pos = Point3()
        far_pos = Point3()
        base.camLens.extrude(self.pos, near_pos, far_pos)
        if self.plane.intersectsLine(pos,
            render.getRelativePoint(camera, near_pos),
            render.getRelativePoint(camera, far_pos)):
            pos = int(round(pos[0])), int(round(pos[1]))
            self.pointer.setPos(pos[0], pos[1], 0.1)
            self._update_text(pos)

    def _update_text(self, pos):
        poses = [p for p, i in self.editor.map]
        offset_x = -min(p[0] for p in poses)
        offset_y = -min(p[1] for p in poses)
        pos = max(pos[0] + offset_x, 0), max(pos[1] + offset_y, 0)
        txt = '{0}, {1}'.format(*pos)
        self.editor.coordinate_text.setText(txt)