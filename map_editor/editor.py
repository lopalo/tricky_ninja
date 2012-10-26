import sys
sys.path.insert(0, '')
from os import path
import __builtin__
from copy import deepcopy
import yaml
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
        self.map_name = map_name
        self.stop_loop = False
        self.current_group = None
        self._group_markers = set()
        self.map = Map(map_name)
        self.map_builder = MapBuilder(self.map, render)
        self.map_builder.build()
        self.edit_panel = EditPanel(self)
        self.pointer = Pointer(self)
        taskMgr.add(self.pointer.update, 'update_pointer')
        self.camera_node = render.attachNewNode('camera_node')
        self.set_camera_control()
        base.accept('escape', self.esc_handler)
        base.accept('s', self.save)

    def set_camera_control(self, only_arrows=False):
        pitch = -ES.camera['horizontal_angle']
        yaw = ES.camera['init_vertical_angle']
        min_h = ES.camera['min_height']
        max_h = ES.camera['max_height']
        height = ES.camera['init_height']
        pos = ES.camera['init_pos']
        hstep = ES.camera['height_step']
        camera_node = self.camera_node
        if not only_arrows:
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

    def remove_arrow_handlers(self):
        base.ignore('arrow_left')
        base.ignore('arrow_left-repeat')
        base.ignore('arrow_right')
        base.ignore('arrow_right-repeat')
        base.ignore('arrow_up')
        base.ignore('arrow_up-repeat')
        base.ignore('arrow_down')
        base.ignore('arrow_down-repeat')

    def select_group(self, ident):
        self.edit_panel.select_group(ident)

    def set_current_group(self, group):
        self.current_group = group
        self._mark_group()

    def _mark_group(self):
        for marker in self._group_markers:
            marker.removeNode()
        self._group_markers.clear()
        if self.current_group is None:
            return
        for pos in self.map.groups[self.current_group['ident']]:
            marker = loader.loadModel(S.model('plane'))
            texture = loader.loadTexture(S.texture('black_pointer'))
            marker.setTexture(texture)
            marker.setTransparency(True)
            marker.setHpr(0, -90, 0)
            marker.reparentTo(render)
            marker.setPos(pos[0], pos[1], 0.1)
            marker.setBin("fixed", 40)
            marker.setDepthTest(False)
            marker.setDepthWrite(False)
            self._group_markers.add(marker)

    def save(self):
        map = self.map
        offset_x, offset_y = 0, 0
        poses = [p for p, i in map]
        min_x = min(p[0] for p in poses)
        if min_x < 0:
            offset_x = -min_x
        min_y = min(p[1] for p in poses)
        if min_y < 0:
            offset_y = -min_y
        width = max(p[0] for p in poses) - min_x + 1
        height = max(p[1] for p in poses) - min_y + 1
        topology = [['..'] * width for _ in range(height)]
        for ident, gposes in map.groups.items():
            for p in gposes:
                topology[p[1] + offset_y][p[0] + offset_x] = ident
        topology = [' '.join(row) for row in topology]
        topology.reverse()
        yaml_data = map.yaml_data
        definitions = deepcopy(map.definitions)
        yaml_data['topology'] = topology
        yaml_data['substrate_actions'] = definitions.pop('ss')['actions']
        yaml_data['definitions'] = definitions
        #TODO: apply offset to routes
        with open(S.map(self.map_name), 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, width=1000)

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