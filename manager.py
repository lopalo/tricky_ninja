from os import path
from glob import glob
from collections import deque
from panda3d.core import *
from map import Map


class BuildWorldError(Exception):
    pass


class MapTextureError(BuildWorldError):
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
                self._set_texture(info['texture'], info['ident'], coord)
                continue
            elif kind == 'model':
                model = loader.loadModel(S.model(info['model']))
                model.reparentTo(render)
                angle = info.get('angle', 0)
                model.setHpr(angle, 0, 0)
                if 'size' in info:
                    model.setScale(info['size'])
                else:
                    model.setScale(S.model_size(info['model']))
                model.setPos(coord[0], coord[1], 0)
            elif kind == 'chain_model':
                self._set_chain_model(
                info['vertical_model'],
                info['left_bottom_model'],
                info['ident'],
                coord
            )
            elif kind == 'sprite':
                sprite = loader.loadModel(S.model('plane'))
                texture = loader.loadTexture(S.texture(info['texture']))
                texture.setWrapU(Texture.WMClamp)
                texture.setWrapV(Texture.WMClamp)
                sprite.setTexture(texture)
                sprite.reparentTo(render)
                sprite.setTransparency(True)
                sprite.reparentTo(render)
                size = info.get('size', 1.0)
                sprite.setScale(size)
                sprite.setPos(coord[0], coord[1], size / 2)
                sprite.setBillboardAxis()

            self._set_texture(None, None, coord, True)

    def _load_textures(self):
        self.map_textures = {}
        for txt_name in self.map.textures:
            txt_paths = glob(path.join(S.map_texture(txt_name), '*.png'))
            if len(txt_paths) == 5:
                names = [path.basename(i).split('.')[0] for i in txt_paths]
                if set(names) != set(self.texture_names):
                    raise MapTextureError(
                            'Wrong part names ({0})'.format(txt_name))
                self.map_textures[txt_name] = parts = [{}, {}, {}, {}]
                images = dict((name, PNMImage(Filename(path)))
                        for name, path in zip(names, txt_paths))
                for name, i in images.items():
                    if i.getXSize() != i.getYSize():
                        raise MapTextureError(
                            'Parts must be square ({0})'.format(txt_name))
                    size = S.map_texture_size
                    image = PNMImage(size, size)
                    image.addAlpha()
                    image.quickFilterFrom(i)
                    w, h = size / 2, size / 2
                    for num, (x, y) in enumerate(((0, 0), (w, 0),
                                                  (w, h), (0, h))):
                        sub_i = PNMImage(w, h)
                        sub_i.addAlpha()
                        sub_i.copySubImage(image, 0, 0, x, y, w, h)
                        parts[num][name] = sub_i
            elif len(txt_paths) > 1 or len(txt_paths) == 0:
                raise MapTextureError(
                        'Wrong count of parts ({0})'.format(txt_name))
            else:
                texture = txt_paths[0]
                if path.basename(texture).split('.')[0] != 'main':
                    raise MapTextureError(
                        'Wrong name of main part ({0})'.format(txt_name))
                self.map_textures[txt_name] = PNMImage(texture)


    def _set_texture(self, txt_name, ident, pos, only_ss=False):
        ss_textures = self.map_textures[self.map.substrate_texture]
        size = S.map_texture_size
        result_image = PNMImage(size, size)
        result_image.addAlpha()
        w, h = size / 2, size / 2

        nbs = dict(self.map.neighbors(pos, True, True))
        t, tr = nbs.get('top'), nbs.get('top-right')
        r, rb = nbs.get('right'), nbs.get('right-bottom')
        b, bl = nbs.get('bottom'), nbs.get('bottom-left')
        l, lt = nbs.get('left'), nbs.get('left-top')
        nbs = deque((l, lt, t, tr, r, rb, b, bl))
        #draws substrate multipart texture
        for num, (x, y) in enumerate(((0, 0), (w, 0),
                                      (w, h), (0, h))):
            c = tuple(nbs)[:3]
            if all(c):
                ss_img = ss_textures[num]['center']
            elif c[0] and c[2]:
                ss_img = ss_textures[num]['corners']
            elif c[0]:
                if num % 2 == 0:
                    ss_img = ss_textures[num]['horizontal']
                else:
                    ss_img = ss_textures[num]['vertical']
            elif c[2]:
                if num % 2 == 0:
                    ss_img = ss_textures[num]['vertical']
                else:
                    ss_img = ss_textures[num]['horizontal']
            else:
                ss_img = ss_textures[num]['main']
            nbs.rotate(-2)
            result_image.copySubImage(ss_img, x, y, 0, 0, w, h)

        if not only_ss:
            textures = self.map_textures[txt_name]
            mpart = type(textures) is list
            if mpart:
                #draws multipart texture
                for num, (x, y) in enumerate(((0, 0), (w, 0),
                                              (w, h), (0, h))):
                    c = tuple(nbs)[:3]
                    if all(c) and all(i.get('ident') == ident
                                                    for i in c):
                        img = textures[num]['center']
                    elif (c[0] and c[2] and c[0].get('ident') == ident
                                        and c[2].get('ident') == ident):
                        img = textures[num]['corners']
                    elif c[0] and c[0].get('ident') == ident:
                        if num % 2 == 0:
                            img = textures[num]['horizontal']
                        else:
                            img = textures[num]['vertical']
                    elif c[2] and c[2].get('ident') == ident:
                        if num % 2 == 0:
                            img = textures[num]['vertical']
                        else:
                            img = textures[num]['horizontal']
                    else:
                        img = textures[num]['main']
                    nbs.rotate(-2)
                    result_image.blendSubImage(img, x, y, 0, 0, w, h)
            else:
                #draws single texture
                img = textures
                result_image.blendSubImage(img, 0, 0, 0, 0, size, size)

        plane = loader.loadModel(S.model('plane'))
        texture = Texture()
        texture.load(result_image)
        texture.setWrapU(Texture.WMClamp)
        texture.setWrapV(Texture.WMClamp)
        plane.setTexture(texture)
        plane.setHpr(0, -90, 0)
        plane.reparentTo(render)
        plane.setTransparency(True)
        plane.setPos(pos[0], pos[1], 0)

    def _set_chain_model(self, vm, lbm, ident, pos):
        nbs = dict(self.map.neighbors(pos, yield_names=True))
        t, r = nbs.get('top'), nbs.get('right')
        b, l = nbs.get('bottom'), nbs.get('left')
        nbs = deque((t, r, b, l))
        count = len([i for i in nbs if i and i.get('ident') == ident])
        if count == 0 or count > 2:
            model_name, angle = vm, 0
        elif count == 1:
            model_name = vm
            for num, i in enumerate(nbs):
                if i and i.get('ident') == ident:
                    angle = -90 * num
                    break
        elif count == 2:
            if (t and b and t.get('ident') == ident
                        and b.get('ident') == ident):
                model_name, angle = vm, 0
            elif (l and r and l.get('ident') == ident
                          and r.get('ident') == ident):
                model_name, angle = vm, 90
            else:
                for num in range(4):
                    f, s= tuple(nbs)[:2]
                    if (f and s and f.get('ident') == ident
                                and s.get('ident') == ident):
                        model_name, angle = lbm, -90 * num
                        break
                    nbs.rotate(-1)
        model = loader.loadModel(S.model(model_name))
        model.reparentTo(render)
        model.setScale(0.016)
        model.setScale(S.model_size(model_name))
        model.setPosHpr(pos[0], pos[1], 0, angle, 0, 0)

    def __call__(self, task):
        pass #TODO: implement actions per frame

    def block(self, x, y):
        pass

    def is_availale(self, x, y):
        pass #is existed on map and not in blocked_squares

    def unblock(self):
        pass

