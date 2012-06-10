from collections import OrderedDict
import yaml


class MapDataError(Exception):
    pass

def check_map_data(data):
    stop = False
    for f in ('substrate-texture', 'definitions', 'topology'):
        if f not in data:
            stop = True
            yield f, 'is not specified'
    if stop: return
    if type(data['substrate-texture']) is not str:
        yield 'substrate-texture', 'is not a string'
    for id, info in data['definitions'].items():
        if len(id) != 2:
            yield ('definitions',
                "ident '{0}' should contain two characters".format(id))
        for row in data['topology']:
            if id in row:
                break
        else:
            yield 'definitions', "'{0}' is not in topology".format(id)
        if info['kind'] == 'texture':
            if 'texture' not in info:
                yield ('definitions',
                    "value of '{0}' doesn't have texture name".format(id))
                continue
            if type(info['texture']) is not str:
                yield ('definitions',
                    "texture name for '{0}' is not a string".format(id))
        elif info['kind'] == 'model':
            if 'angle' in info and type(info['angle']) is not int:
                yield ('definitions',
                    "angle for '{0}' is not an integer".format(id))
            if 'model' not in info:
                yield ('definitions',
                    "value of '{0}' doesn't have model name".format(id))
                continue
            if type(info['model']) is not str:
                yield ('definitions',
                    "model name for '{0}' is not a string".format(id))
            if 'size' in info:
                size = info['size']
                if type(size) is not float:
                    yield ('definitions',
                    "model size for '{0}' is not a float".format(id))
                elif size <= 0:
                    yield ('definitions',
                    "model size for '{0}' must be positive".format(id))
        elif info['kind'] == 'chain_model':
            for name in ('vertical_model', 'left_bottom_model'):
                if name not in info:
                    yield ('definitions',
                    "value of '{0}' doesn't have {1} name".format(
                                                            id, name))
                elif type(info[name]) is not str:
                    yield ('definitions',
                    "{0} name for '{1}' is not a string".format
                                                            (name, id))
        elif info['kind'] == 'sprite':
            if 'texture' not in info:
                yield ('definitions',
                    "value of '{0}' doesn't have texture name".format(id))
                continue
            if type(info['texture']) is not str:
                yield ('definitions',
                    "texture name for '{0}' is not a string".format(id))
            if 'size' in info:
                size = info['size']
                if type(size) is not float:
                    yield ('definitions',
                    "sprite size for '{0}' is not a float".format(id))
                elif size <= 0:
                    yield ('definitions',
                    "sprite size for '{0}' must be positive".format(id))
        else:
            yield 'definitions', "unknown kind for '{0}'".format(id)
    length = len(data['topology'][0])
    for row in data['topology']:
        if (len(row) + 1) % 3:
            yield 'topology', 'wrong length of row'
        if len(row) != length:
            yield 'topology', 'different count of rows'
        for index in range(0, length, 3):
            id = row[index:index+2]
            if id in ('..', 'ss'):
                continue
            if id not in data['definitions']:
                yield 'topology', 'unknown ident ' + id

class Map(object):
    _neighbors = OrderedDict((
        ('top', (0, 1)),
        ('top-right', (1, 1)),
        ('right', (1, 0)),
        ('right-bottom', (1, -1)),
        ('bottom', (0, -1)),
        ('bottom-left', (-1, -1)),
        ('left', (-1, 0)),
        ('left-top', (-1, 1))
    ))

    def __init__(self, manager, name):
        with open(S.map(name), 'r') as f:
           data = yaml.load(f)
           data['topology'].reverse()
        errors = list(check_map_data(data))
        if errors:
            msg = "\nMap '{0}'\n".format(name.split('.')[0])
            for f, err in errors:
                msg +='{0}: {1}\n'.format(f, err)
            raise MapDataError(msg)
        self.substrate_texture = data['substrate-texture']

        self.textures = set([self.substrate_texture])
        self.data = {}
        for num_row, row in enumerate(data['topology']):
            for index in range(0, len(data['topology'][0]), 3):
                ident = row[index:index+2]
                if ident == '..':
                    continue
                elif ident == 'ss':
                    info = dict(kind='substrate_texture')
                else:
                    info = data['definitions'][ident]
                    info['ident'] = ident
                self.data[index/3, num_row] = info
                if info['kind'] == 'texture':
                    self.textures.add(info['texture'])

    def __getitem__(self, coord):
        return self.data.get(coord)

    def __iter__(self):
        return self.data.items().__iter__()

    def neighbors(self, coord, all=False, yield_names=False):
        keys = self._neighbors.keys()
        keys = keys if all else keys[::2]
        for key in keys:
            offset = self._neighbors[key]
            pos = coord[0] + offset[0], coord[1] + offset[1]
            if self[pos] is not None:
                if yield_names:
                    yield key, self[pos]
                else:
                    yield pos. self[pos]

