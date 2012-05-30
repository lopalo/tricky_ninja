from os import path
from glob import glob
from collections import deque
from panda3d.core import *
from map import Map


class BuildWorldError(Exception):
    pass


class Manager(object):
    texture_names = ['main', 'center', 'horizontal', 'vertical', 'corners']

    def __init__(self, map_name):
        self.blocked_squares = set()
        self.map = Map(self, map_name)
        self.build_world()

    def build_world(self):
        self._load_textures()
        for coord, info in self.map:
            kind = info['kind']
            if kind == 'substrate_texture':
                pass
            elif kind == 'texture':
                txt = self._get_texture(info['texture'],
                                        info['ident'], coord)
                txt.setPos(coord[0], coord[1], 0.001)
            elif kind == 'model':
                pass
            elif kind == 'sprite':
                pass

            txt = self._get_texture(self.map.substrate_texture,
                                                        'ss', coord)
            txt.setPos(coord[0], coord[1], 0)

    def _load_textures(self):
        self.textures = {}
        for txt_name in self.map.textures:
            txt_paths = glob(path.join(S.texture(txt_name), '*.png'))
            if len(txt_paths) == 5:
                names = [path.basename(i).split('.')[0] for i in txt_paths]
                if set(names) != set(self.texture_names):
                    raise BuildWorldError(
                            'Wrong texture names ({0})'.format(txt_name))
                self.textures[txt_name] = parts = [{}, {}, {}, {}]
                images = dict((name, PNMImage(Filename(path)))
                        for name, path in zip(names, txt_paths))
                for name, i in images.items():
                    x, y = i.getXSize() / 2, i.getYSize() / 2
                    for num, (_x, _y) in enumerate(((0, 0), (x, 0),
                                                    (x, y), (0, y))):
                        sub_i = PNMImage(x, y)
                        sub_i.addAlpha()
                        sub_i.copySubImage(i, 0, 0, _x, _y, x, y)
                        texture = Texture()
                        texture.load(sub_i)
                        parts[num][name] = texture

            elif len(txt_paths) > 1 or len(txt_paths) == 0:
                raise BuildWorldError(
                        'Wrong count of textures ({0})'.format(txt_name))
            else:
                texture = txt_paths[0]
                if path.basename(texture).split('.')[0] != 'main':
                    raise BuildWorldError(
                        'Wrong name of texture ({0})'.format(txt_name))
                self.textures[txt_name] = loader.loadTexture(texture)


    def _get_texture(self, txt_name, ident, pos):
        textures = self.textures[txt_name]
        if type(textures) is list:
            #creating parts of a texture
            #TODO: create particular algorithm for 'ss'
            plane = render.attachNewNode("")

            nbs = dict(self.map.neighbors(pos, True, True))
            t, tr = nbs.get('top'), nbs.get('top-right')
            r, rb = nbs.get('right'), nbs.get('right-bottom')
            b, bl = nbs.get('bottom'), nbs.get('bottom-left')
            l, lt = nbs.get('left'), nbs.get('left-top')
            nbs = deque((l, lt, t, tr, r, rb, b, bl))

            for num, pos in enumerate(((-0.25, 0.25), (0.25, 0.25),
                                       (0.25, -0.25), (-0.25, -0.25))):
                c = tuple(nbs)[:3]
                if all(c) and all(i.get('ident') == ident
                                                for i in c):
                    texture = textures[num]['center']
                elif (c[0] and c[2] and c[0].get('ident') == ident
                                    and c[2].get('ident') == ident):
                    texture = textures[num]['corners']
                elif c[0] and c[0].get('ident') == ident:
                    if num % 2 == 0:
                        texture = textures[num]['horizontal']
                    else:
                        texture = textures[num]['vertical']
                elif c[2] and c[2].get('ident') == ident:
                    if num % 2 == 0:
                        texture = textures[num]['vertical']
                    else:
                        texture = textures[num]['horizontal']
                else:
                    texture = textures[num]['main']
                subpl = loader.loadModel(S.model('plane'))
                subpl.setTexture(texture)
                subpl.setScale(0.5)
                subpl.reparentTo(plane)
                subpl.setPosHpr(pos[0], pos[1], 0, 0, -90, 0)
                nbs.rotate(-2)
        else:
            texture = textures
            plane = loader.loadModel(S.model('plane'))
            plane.setTexture(texture)
            plane.setHpr(0, -90, 0)

        plane.reparentTo(render)
        plane.setTransparency(True)
        return plane

    def __call__(self, task):
        pass #TODO: implement actions per frame

    def block(self, x, y):
        pass

    def is_availale(self, x, y):
        pass #is existed on map and not in blocked_squares

    def unblock(self):
        pass

