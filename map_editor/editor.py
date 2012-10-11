import sys
sys.path.insert(0, '')
from os import path
import __builtin__
from direct.showbase.ShowBase import ShowBase
from settings import Settings, BaseSettings
from map_model.map import Map
from map_builder import MapBuilder
from map_editor.edit_panel import EditPanel
from map_editor.pointer import Pointer

class Editor(ShowBase):

    def __init__(self, map_name):
        ShowBase.__init__(self)
        self.disableMouse()
        self.stop_loop = False
        self.current_group = None
        base.accept('escape', self.esc_handler)
        self.map = Map(map_name)
        #FIXME: delete
        self.current_group = dict(
            kind='substrate_texture',
            actions=[]
        )
        self.map_builder = MapBuilder(self.map, render)
        self.map_builder.build()
        self.edit_panel = EditPanel(self)
        self.pointer = Pointer(self)
        taskMgr.add(self.pointer.update, 'update_pointer')
        self.set_camera_control()

    def set_camera_control(self):
        pitch = -ES.camera['horizontal_angle']
        yaw = ES.camera['init_vertical_angle']
        min_h = ES.camera['min_height']
        max_h = ES.camera['max_height']
        height = ES.camera['init_height']
        pos = ES.camera['init_pos']
        hstep = ES.camera['height_step']
        self.camera_node = camera_node = render.attachNewNode('camera_node')
        camera.reparentTo(camera_node)
        def init():
            camera_node.setPosHpr(pos[0], pos[1], height, 90 + yaw, 0, 0)
            camera.setPosHpr(0, 0, 0, 0, pitch, 0)
        init()
        base.accept('home', init)
        def incr_angle():
            camera_node.setH(camera_node, ES.camera['vertical_angle_step'])
        base.accept('arrow_left', incr_angle)
        base.accept('arrow_left-repeat', incr_angle)
        def incr_angle():
            camera_node.setH(camera_node, -ES.camera['vertical_angle_step'])
        base.accept('arrow_right', incr_angle)
        base.accept('arrow_right-repeat', incr_angle)
        def incr_height():
            camera_node.setZ(min(camera_node.getZ() + hstep, max_h))
        base.accept('arrow_up', incr_height)
        base.accept('arrow_up-repeat', incr_height)
        def decr_height():
            camera_node.setZ(max(camera_node.getZ() - hstep, min_h))
        base.accept('arrow_down', decr_height)
        base.accept('arrow_down-repeat', decr_height)


    def esc_handler(self):
        self.stop_loop = True

    def loop(self):
        while not self.stop_loop:
            taskMgr.step()

if __name__ == '__main__':
    __builtin__.S = Settings('settings.yaml')
    __builtin__.ES = BaseSettings('map_editor/settings.yaml')
    assert len(sys.argv) == 2, 'The map name is not specified'
    map_path = S.map(sys.argv[1])
    assert path.exists(map_path), 'The map does not exist'
    assert path.isfile(map_path), 'The map is not a file'
    Editor(sys.argv[1]).loop()