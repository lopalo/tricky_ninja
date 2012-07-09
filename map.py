from math import atan2, hypot, degrees
from collections import OrderedDict, defaultdict, deque
import yaml


AVAILABLE_ACTIONS = ('walk', 'jump', 'see')


def segment_crossing(segm1, segm2):
    x_cross = None
    x_diff1 = float(segm1[1][0] - segm1[0][0])
    y_diff1 = float(segm1[1][1] - segm1[0][1])
    if x_diff1 != 0:
        a1 = y_diff1 / x_diff1
        b1 = segm1[0][1] - a1 * segm1[0][0]
    else:
        a1 = float('inf')
        x_cross = segm1[0][0]
    x_diff2 = float(segm2[1][0] - segm2[0][0])
    y_diff2 = float(segm2[1][1] - segm2[0][1])
    if x_diff2 != 0:
        a2 = y_diff2 / x_diff2
        b2 = segm2[0][1] - a2 * segm2[0][0]
    else:
        a2 = float('inf')
        x_cross = segm2[0][0]
    if a1 == a2:
        return # they are parallel
    if x_cross is None:
        x_cross = (b2 - b1) / (a1 - a2)
    if a1 != float('inf'):
        y_cross = a1 * x_cross + b1
    else:
        y_cross = a2 * x_cross + b2
    if not (min(segm1[0][0], segm1[1][0]) <= x_cross
            <= max(segm1[0][0], segm1[1][0])):
        return
    if not (min(segm1[0][1], segm1[1][1]) <= y_cross # for a vertical segment
            <= max(segm1[0][1], segm1[1][1])):
        return
    if not (min(segm2[0][0], segm2[1][0]) <= x_cross
            <= max(segm2[0][0], segm2[1][0])):
        return
    if not (min(segm2[0][1], segm2[1][1]) <= y_cross # for a vertical segment
            <= max(segm2[0][1], segm2[1][1])):
        return
    return x_cross, y_cross

def square_sides(pos):
    x, y = pos
    vertices = deque(((-.5, .5), (.5, .5), (.5, -.5), (-.5, -.5)))
    for _ in range(4):
        v1, v2 = tuple(vertices)[:2]
        yield (x + v1[0], y + v1[1]), (x + v2[0], y + v2[1])
        vertices.rotate(-1)


class MapDataError(Exception):
    pass


# maps kinds to dicts with fields
fields_declaration = {
    'texture': {
        'texture': {
            'type': str
        },
    },
    'model': {
        'model': {
            'type' : str
        },
        'angle': {
            'type': int,
            'default': True
        },
        'size': {
            'type': float,
            'default': True,
            'positive': True
        }
    },
    'chain_model': {
        'vertical_model': {
            'type': str
        },
        'left_bottom_model': {
            'type': str
        },
    },
    'sprite': {
        'texture': {
            'type': str
        },
        'size': {
            'type': float,
            'default': True,
            'positive': True,
        }
    }
}



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
        actions = info.get('actions')
        if actions is not None and actions not in data['action_groups']:
            yield ('definitions',
                    "unknown action group for '{0}'".format(id))
        kind = info.get('kind')
        if kind is None:
            continue
        elif kind not in fields_declaration:
            yield 'definitions', "unknown kind for '{0}'".format(id)
            continue
        fields = fields_declaration[kind]
        for f, i in fields.items():
            if not i.get('default', False) and f not in info:
                yield ('definitions',
                "value of '{0}' doesn't contain '{1}' field".format(id, f))
            if f not in info:
                continue
            if not isinstance(info[f], i['type']):
                t_name = i['type'].__name__
                yield ('definitions',
                "field '{0}' of '{1}' is not {2}".format(f, id, t_name))
            if i.get('positive') and info[f] <= 0:
                yield ('definitions',
                "field '{0}' of '{1}' must be positive".format(f, id))

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
            if a not in AVAILABLE_ACTIONS:
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

    def view_field(self, pos, angle, cone_angle, radius, pred):
        assert 0 <= angle < 360, angle
        assert 0 < cone_angle < 180, cone_angle
        st_a, end_a = angle - cone_angle / 2 , angle + cone_angle / 2
        def field_pred(sq):
            diff = sq[0] - pos[0], sq[1] - pos[1]
            if hypot(diff[0], diff[1]) > radius:
                return False
            sq_angle = degrees(atan2(diff[1], diff[0]))
            if 90 < angle < 270:
                sq_angle %= 360
            elif 270 <= angle < 360:
                sq_angle += 360
            if not st_a < sq_angle < end_a:
                return False
            if not pred(sq):
                obstacles.add(sq)
                return False
            for obst in obstacles:
                for side in square_sides(obst):
                    if segment_crossing((pos, sq), side) is not None:
                        return False
            return True

        obstacles = set()
        field = sum(self.wave(pos), [])
        return set(i for i in field if field_pred(i))

    def block(self, pos):
        assert self[pos] and pos not in self.blocked_squares
        self.blocked_squares.add(pos)

    def is_available(self, pos):
        return pos in self and pos not in self.blocked_squares

    def unblock(self, pos):
        self.blocked_squares.remove(pos)