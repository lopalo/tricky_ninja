from collections import OrderedDict
import yaml


class MapDataError(Exception):
    pass

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
        try:
            self._check_data(data)
        except (AssertionError, MapDataError) as e:
            raise MapDataError(e.message + ' ({0})'.format(name))
        self.substrate_texture = data['substrate-texture']

        self.textures = set([self.substrate_texture])
        self.models = set()
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
                if info['kind'] == 'model':
                    self.models.add(info['model'])

    def _check_data(self, data):
        assert 'substrate-texture' in data, (
                        "'substrate-texture' is not specified")
        assert type(data['substrate-texture']) is str, (
                        "'substrate-texture' is not a string")
        assert 'definitions' in data, (
                        "'definitions' is not specified")
        assert 'topology' in data and data['topology'], (
                        "'topology' is not specified")
        for id, info in data['definitions'].items():
            assert len(id) == 2, 'Ident should contain two characters'
            for row in data['topology']:
                if id in row:
                    break
            else:
                raise MapDataError("'{0}' is not in topology".format(id))
            if info['kind'] == 'texture':
                assert 'texture' in info, (
                "Value of '{0}' doesn't have texture name'".format(id))
                assert type(info['texture']) is str, (
                    "Texture name for '{0}' is not a string".format(id))
            elif info['kind'] == 'model':
                pass
            else:
                raise MapDataError("Unknown kind for '{0}'".format(id))
        length = len(data['topology'][0])
        for row in data['topology']:
            assert len(row) == length, (
                "Topology has different count of rows")
            for index in range(0, length, 3):
                id = row[index:index+2]
                if id in ('..', 'ss'):
                    continue
                assert id in data['definitions'], 'Unknown ident ' + id

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

