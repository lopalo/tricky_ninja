import sys
sys.path.insert(0, '')
from os import path
import __builtin__
from copy import deepcopy
import string
import random
import yaml
from direct.showbase.ShowBase import ShowBase
from settings import Settings, BaseSettings
from map_model.map import Map
from map_builder import MapBuilder
from map_editor.edit_panel import EditPanel
from map_editor.pointer import Pointer
from misc.display_text import display_control_keys

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
        base.accept(ES.control_keys['cancel_selection'], self.cancel_selection)
        base.accept(ES.control_keys['close_window'], self.close_window)
        base.accept(ES.control_keys['save'], self.save)
        base.accept(ES.control_keys['add_group'], self.add_group)
        base.accept(ES.control_keys['switch_transparency'],
                                self.switch_transparency)
        if ES.show_control_keys:
            display_control_keys(ES)

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
        key = ES.control_keys['rotate_camera_counterclockwise']
        base.accept(key, incr_angle)
        base.accept(key + '-repeat', incr_angle)
        def decr_angle():
            camera_node.setH(camera_node, -ES.camera['vertical_angle_step'])
        key = ES.control_keys['rotate_camera_clockwise']
        base.accept(key, decr_angle)
        base.accept(key + '-repeat', decr_angle)
        def incr_height():
            camera_node.setZ(min(camera_node.getZ() + hstep, max_h))
        key = ES.control_keys['increase_camera_height']
        base.accept(key, incr_height)
        base.accept(key + '-repeat', incr_height)
        def decr_height():
            camera_node.setZ(max(camera_node.getZ() - hstep, min_h))
        key = ES.control_keys['decrease_camera_height']
        base.accept(key, decr_height)
        base.accept(key + '-repeat', decr_height)

    def remove_arrow_handlers(self):
        key = ES.control_keys['rotate_camera_counterclockwise']
        base.ignore(key)
        base.ignore(key + '-repeat')
        key = ES.control_keys['rotate_camera_clockwise']
        base.ignore(key)
        base.ignore(key + '-repeat')
        key = ES.control_keys['increase_camera_height']
        base.ignore(key)
        base.ignore(key + '-repeat')
        key = ES.control_keys['decrease_camera_height']
        base.ignore(key)
        base.ignore(key + '-repeat')

    def cancel_selection(self):
        self.select_group(None)

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

    def add_group(self):
        letters = string.uppercase + string.lowercase
        while True:
            group_id = random.choice(letters) + random.choice(letters)
            if group_id not in self.map.definitions:
                break
        group = dict(ident=group_id, kind='empty', actions=[])
        self.map.definitions[group_id] = group
        self.edit_panel.add_group(group_id)

    def save(self):
        map = self.map
        offset_x, offset_y = 0, 0
        poses = [p for p, i in map]
        min_x = min(p[0] for p in poses)
        offset_x = -min_x
        min_y = min(p[1] for p in poses)
        offset_y = -min_y
        width = max(p[0] for p in poses) - min_x + 1
        height = max(p[1] for p in poses) - min_y + 1
        topology = [['..'] * width for _ in range(height)]
        for ident, gposes in map.groups.items():
            for p in gposes:
                topology[p[1] + offset_y][p[0] + offset_x] = ident
        topology = [' '.join(row) for row in topology]
        topology.reverse()
        yaml_data = deepcopy(map.yaml_data)
        definitions = deepcopy(map.definitions)
        for info in tuple(definitions.values()):
            if not map.groups[info['ident']]:
                del definitions[info['ident']]
            del info['ident']
            if info['kind'] == 'model_field':
                del info['actions']
        yaml_data['topology'] = topology
        yaml_data['substrate_actions'] = definitions.pop('ss')['actions']
        yaml_data['definitions'] = definitions
        if 'start_position' in yaml_data:
            st_pos = yaml_data['start_position']
            st_pos = [st_pos[0] + offset_x, st_pos[1] + offset_y]
            yaml_data['start_position'] = st_pos
        if 'routes' in yaml_data:
            routes = yaml_data['routes']
            for rname, route in routes.items():
                for index, rpos in  enumerate(tuple(route)):
                    route[index] = [rpos[0] + offset_x, rpos[1] + offset_y]
        with open(S.map(self.map_name), 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, width=1000)

    def switch_transparency(self):
        if self.map_builder.models_transparency == 1:
            self.map_builder.set_models_transparency(ES.model_transparency)
        else:
            self.map_builder.set_models_transparency(1)

    def close_window(self):
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