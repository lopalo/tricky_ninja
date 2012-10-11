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

        self.plane = plane = Plane((0, 0, 0), (1, 1, 0), (1, 0, 0))

        base.accept('mouse1', self.on_left_click)

    @property
    def pos(self):
        return base.mouseWatcherNode.getMouse()

    @property
    def map_pos(self):
        pos = self.pointer.getPos()
        return int(pos[0]), int(pos[1])

    def on_left_click(self):
        if not self.map_pointer:
            return
        cur_g = self.editor.current_group
        if cur_g is None:
            if self.map_pos in self.editor.map:
                del self.editor.map[self.map_pos]
        else:
            self.editor.map[self.map_pos] = cur_g
        self.editor.map_builder.redraw_9_squares(self.map_pos, cur_g)

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
            self.pointer.setPos(round(pos[0]), round(pos[1]), 0.1)
