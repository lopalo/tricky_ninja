from os import path
from glob import glob
from map import Map

class BuildWorldError(Exception):
    pass

class Manager(object):
    texture_names = ['main', 'top', 'top-right', 'bottom', 'top-bottom']

    def __init__(self, map_name):
        self.blocked_squares = set()
        self.map = Map(self, map_name)
        self.build_world()

    def build_world(self):
        for coord, info in self.map:
            kind = info['kind']
            if kind == 'substrate_texture':
                pass
            elif kind == 'texture':
                txt = self._get_texture(info['texture'], info['ident'])
                txt.setPos(coord[0], coord[1], 0.001)
            elif kind == 'model':
                pass
            elif kind == 'sprite':
                pass

            txt = self._get_texture(self.map.substrate_texture, 'ss')
            txt.setPos(coord[0], coord[1], 0)

    def _get_texture(self, txt_name, ident):
        txt_paths = glob(path.join(S.texture(txt_name), '*.png'))
        if len(txt_paths) == 5:
            names = [path.basename(i).split('.')[0] for i in txt_paths]
            if names != texture_names:
                raise BuildWorldError(
                        'Wrong texture names ({0})'.format(txt_name))
            #TODO: choose right texture and angle
        elif len(txt_paths) > 1 or len(txt_paths) == 0:
            raise BuildWorldError(
                    'Wrong count of textures ({0})'.format(txt_name))
        else:
            texture = txt_paths[0]
            if path.basename(texture).split('.')[0] != 'main':
                raise BuildWorldError(
                    'Wrong name of texture ({0})'.format(txt_name))

        plane = loader.loadModel(S.model('plane'))
        plane.setTexture(loader.loadTexture(texture))
        plane.reparentTo(render)
        plane.setTransparency(True)
        plane.setHpr(0, -90, 0) #set angle that depends on texture name
        return plane

    def __call__(self, task):
        pass #TODO: implement actions per frame

    def block(self, x, y):
        pass

    def is_availale(self, x, y):
        pass #is existed on map and not in blocked_squares

    def unblock(self):
        pass

