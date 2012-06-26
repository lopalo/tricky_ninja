from collections import OrderedDict, defaultdict
import yaml


class MapDataError(Exception):
    pass

available_actions = ('walk', 'jump',)

def check_map_data(data):
    stop = False
    for f in ('substrate_texture', 'definitions',
              'topology', 'action_groups'):
        if f not in data:
            stop = True
            yield f, 'is not specified'
    if stop: return
    if type(data['substrate_texture']) is not str:
        yield 'substrate_texture', 'is not a string'
    actions = data['substrate_actions']
    if actions is not None and actions not in data['action_groups']:
            yield ('substrate_actions', "unknown action group")
    for id, info in data['definitions'].items():
        if len(id) != 2:
            yield ('definitions',
                "ident '{0}' should contain two characters".format(id))
        for row in data['topology']:
            if id in row:
                break
        else:
            yield 'definitions', "'{0}' is not in topology".format(id)
        kind = info.get('kind')
        if kind == 'texture':
            if 'texture' not in info:
                yield ('definitions',
                    "value of '{0}' doesn't have texture name".format(id))
                continue
            if type(info['texture']) is not str:
                yield ('definitions',
                    "texture name for '{0}' is not a string".format(id))
        elif kind == 'model':
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
        elif kind == 'chain_model':
            for name in ('vertical_model', 'left_bottom_model'):
                if name not in info:
                    yield ('definitions',
                    "value of '{0}' doesn't have {1} name".format(
                                                            id, name))
                elif type(info[name]) is not str:
                    yield ('definitions',
                    "{0} name for '{1}' is not a string".format
                                                            (name, id))
        elif kind == 'sprite':
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
        elif kind is None:
            pass
        else:
            yield 'definitions', "unknown kind for '{0}'".format(id)
        actions = info.get('actions')
        if actions is not None and actions not in data['action_groups']:
            yield ('definitions',
                    "unknown action group for '{0}'".format(id))

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

    used_action_groups = set(i['actions'] for i in
                             data['definitions'].values()
                             if i.get('actions') is not None)
    unused = set(data['action_groups']) - used_action_groups
    if unused:
        yield 'action_groups', 'Unused groups ' + str(list(unused))
    for k, v in data['action_groups'].items():
        for a in v:
            if a not in available_actions:
                yield ('action_groups',
                    "'{0}' contains unknown action".format(k))


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

    _reverse_neighbors = dict((v, k) for k, v in _neighbors.items())

    def __init__(self, name=None, data=None, check=True):
        if data is None:
            with open(S.map(name), 'r') as f:
                data = yaml.load(f)
        data['topology'].reverse()
        errors = list(check_map_data(data))
        if errors and check:
            msg = "\nMap '{0}'\n".format(name.split('.')[0])
            for f, err in errors:
                msg +='{0}: {1}\n'.format(f, err)
            raise MapDataError(msg)
        self.blocked_squares = set()
        self.substrate_texture = data['substrate_texture']

        self.textures = set([self.substrate_texture])
        self.groups = defaultdict(list)
        self.data = {}
        for info in data['definitions'].values():
            actions = info.get('actions')
            if actions is not None:
                info['actions'] = data['action_groups'][actions]
            else:
                info['actions'] = tuple()
        for num_row, row in enumerate(data['topology']):
            for index in range(0, len(data['topology'][0]), 3):
                ident = row[index:index+2]
                if ident == '..':
                    continue
                elif ident == 'ss':
                    actions = data['substrate_actions']
                    info = dict(
                        kind='substrate_texture',
                        actions=data['action_groups'][actions]
                    )
                else:
                    info = data['definitions'][ident]
                    info['ident'] = ident
                self.data[index/3, num_row] = info
                self.groups[ident].append((index/3, num_row))
                if info.get('kind') == 'texture':
                    self.textures.add(info['texture'])

    def __getitem__(self, coord):
        return self.data.get(coord)

    def __iter__(self):
        return self.data.items().__iter__()

    def __contains__(self, coord):
        return coord in self.data

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
                    yield pos, self[pos]

    def corners(self, coord):
        keys = self._neighbors.keys()
        for key in keys[1::2]:
            offset = self._neighbors[key]
            pos = coord[0] + offset[0], coord[1] + offset[1]
            if pos in self:
                yield pos

    def wave(self, coord, pred=lambda x: True):
        assert self[coord], coord
        wave = [coord]
        visited = set(wave)
        while True:
            new_wave = []
            for c in wave:
                for n, info in self.neighbors(c):
                    if n not in visited and pred(n):
                        new_wave.append(n)
                        visited.add(n)
                for n in self.corners(c):
                    if (n not in visited and pred(n) and
                                self.is_free_corner(c, n, pred)):
                        new_wave.append(n)
                        visited.add(n)
            if len(new_wave) == 0:
                return
            yield new_wave
            wave = new_wave

    def find_path(self, start, end, pred):
        squares = {}
        for num, wave in enumerate(self.wave(start, pred)):
            for c in wave:
                squares[c] = num
                if c == end:
                    return num, squares
        return None, None

    def get_path(self, start, end, pred):
        last_wave_num, squares = self.find_path(start, end, pred)
        if last_wave_num is None:
            return
        path = [end]
        for num, wave in enumerate(self.wave(end, pred)):
            for c in wave:
                if c == start:
                    exit = True
                    break
                num_wave = squares.get(c)
                if num_wave is None:
                    continue
                if num_wave == last_wave_num - num - 1:
                    wave[:] = [c]
                    path.append(c)
        path.reverse()
        return tuple(path)

    def get_jump_field(self, pos):
        for nb1, info in self.neighbors(pos, True):
            pred = lambda pos: 'jump' in self[pos]['actions']
            if self.is_corner(pos, nb1):
                if ('walk' in info['actions'] and
                    'jump' in info['actions'] and
                    self.is_free_corner(pos, nb1, pred)):
                    yield nb1
            elif 'jump' in info['actions']:
                diff = nb1[0] - pos[0], nb1[1] - pos[1]
                nb2 = nb1[0] + diff[0], nb1[1] + diff[1]
                if (nb2 in self and
                    'walk' in self[nb2]['actions'] and
                    'jump' in info['actions']):
                    yield nb2

    def is_corner(self, first, second):
        diff = second[0] - first[0], second[1] - first[1]
        return len(self._reverse_neighbors[diff].split('-')) == 2

    def is_free_corner(self, first, second, pred=lambda pos: True):
        assert self.is_corner(first, second)
        diff = second[0] - first[0], second[1] - first[1]
        nb_names = self._reverse_neighbors[diff].split('-')
        for nb_name in nb_names:
            nb_diff = self._neighbors[nb_name]
            nb_pos = first[0] + nb_diff[0], first[1] + nb_diff[1]
            if nb_pos not in self:
                return False
            if not pred(nb_pos):
                return False
        return True

    def block(self, pos):
        assert self[pos] and pos not in self.blocked_squares
        self.blocked_squares.add(pos)

    def is_available(self, pos):
        return pos in self and pos not in self.blocked_squares

    def unblock(self, pos):
        self.blocked_squares.remove(pos)