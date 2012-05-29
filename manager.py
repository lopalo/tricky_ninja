from os import path
from glob import glob
from map import Map

class BuildWorldError(Exception):
    pass

class Manager(object):
    texture_names = ['center', 'outer-corner', 'border', 'inner-corner']

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

    def _get_texture(self, txt_name, ident, pos):
        txt_paths = glob(path.join(S.texture(txt_name), '*.png'))
        if len(txt_paths) == 5 or len(txt_paths) == 4:
            names = [path.basename(i).split('.')[0] for i in txt_paths]
            _names = list(names)
            _names.remove('main')
            if set(_names) != set(self.texture_names):
                raise BuildWorldError(
                        'Wrong texture names ({0})'.format(txt_name))

            #creating parts of a texture
            #TODO: create particular algorithm for 'ss'
            plane = render.attachNewNode("")

            textures = dict((name, loader.loadTexture(path))
                    for name, path in zip(names, txt_paths))
            nbs = dict(self.map.neighbors(pos, True, True))
            t, tr = nbs.get('top'), nbs.get('top-right')
            r, rb = nbs.get('right'), nbs.get('right-bottom')
            b, bl = nbs.get('bottom'), nbs.get('bottom-left')
            l, lt = nbs.get('left'), nbs.get('left-top')

            for pos in ((-0.25, 0.25), (0.25, 0.25),
                        (0.25, -0.25), (-0.25, -0.25)):
                if pos == (-0.25, 0.25):
                    _nbs = (l, lt, t)
                    if all(_nbs) and all(i.get('ident') == ident
                                                    for i in _nbs):
                        part_name, angle = 'center', 0
                    elif (l and t and l.get('ident') == ident
                                and t.get('ident') == ident):
                        part_name, angle = 'outer-corner', 0
                    elif l and l.get('ident') == ident:
                        part_name, angle = 'border', 90
                    elif t and t.get('ident') == ident:
                        part_name, angle = 'border', 180
                    else:
                        part_name, angle = 'inner-corner', 180
                if pos == (0.25, 0.25):
                    _nbs = (t, tr, r)
                    if all(_nbs) and all(i.get('ident') == ident
                                                    for i in _nbs):
                        part_name, angle = 'center', 0
                    elif (t and r and t.get('ident') == ident
                                and r.get('ident') == ident):
                        part_name, angle = 'outer-corner', -90
                    elif t and t.get('ident') == ident:
                        part_name, angle = 'border', 0
                    elif r and r.get('ident') == ident:
                        part_name, angle = 'border', 90
                    else:
                        part_name, angle = 'inner-corner', 90
                if pos == (0.25, -0.25):
                    _nbs = (r, rb, b)
                    if all(_nbs) and all(i.get('ident') == ident
                                                    for i in _nbs):
                        part_name, angle = 'center', 0
                    elif (r and b and r.get('ident') == ident
                                and b.get('ident') == ident):
                        part_name, angle = 'outer-corner', 180
                    elif r and r.get('ident') == ident:
                        part_name, angle = 'border', -90
                    elif b and b.get('ident') == ident:
                        part_name, angle = 'border', 0
                    else:
                        part_name, angle = 'inner-corner', 0
                if pos == (-0.25, -0.25):
                    _nbs = (b, bl, l)
                    if all(_nbs) and all(i.get('ident') == ident
                                                    for i in _nbs):
                        part_name, angle = 'center', 0
                    elif (b and l and b.get('ident') == ident
                                and l.get('ident') == ident):
                        part_name, angle = 'outer-corner', 90
                    elif b and b.get('ident') == ident:
                        part_name, angle = 'border', 180
                    elif l and l.get('ident') == ident:
                        part_name, angle = 'border', -90
                    else:
                        part_name, angle = 'inner-corner', -90
                subpl = loader.loadModel(S.model('plane'))
                subpl.setTexture(textures[part_name])
                subpl.setScale(0.5)
                subpl.reparentTo(plane)
                subpl.setPosHpr(pos[0], pos[1], 0, angle, -90, 0)


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

