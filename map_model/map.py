from math import atan2, hypot, degrees
from collections import OrderedDict, defaultdict, deque
import yaml
from map_model.check import MapDataError, check_map_data as check_data


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
        self._name = name
        self._check = check
        self._raise_error_message(check_data(data))
        self.blocked_squares = set()
        self.start_pos = data['start_position']
        self.substrate_texture = data['substrate_texture']

        self.textures = set([self.substrate_texture])
        self.groups = defaultdict(list) # need for tests
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
        self.routes = {}
        for key, value in data.get('routes', {}).items():
            self.routes[key] = tuple(tuple(i) for i in value)
        self.npcs = data.get('npcs', tuple())
        self._raise_error_message(self._check_routes())

    def _raise_error_message(self, errors):
        errors = tuple(errors)
        if errors and self._check:
            msg = "\nMap '{0}'\n".format(self._name.split('.')[0])
            for f, err in errors:
                msg +='{0}: {1}\n'.format(f, err)
            raise MapDataError(msg)

    def _check_routes(self):
        for key, route in self.routes.items():
            check_path = True
            for num, pos in enumerate(route):
                if pos not in self:
                    error = ("{0} position of route '{1}' "
                            "doesn't exist on the map").format(num, key)
                    yield 'route', error
                    check_path = False
                    continue

            if check_path:
                pred = lambda pos: 'walk' in self[pos]['actions']
                route = deque(route)
                for _ in range(len(route)):
                    s, e = tuple(route)[:2]
                    error = ("{0} - {1} interval of route '{2}' "
                            "is not passable").format(s, e, key)
                    if self.get_path(s, e, pred) is None:
                        yield 'route', error
                    route.rotate(1)
        for num, npc in enumerate(self.npcs):
            r = npc['route']
            max_count = len(self.routes[r]) - 1
            error = ("{0}: max count for "
                     "route '{1}' is {2}").format(num, r, max_count)
            if npc['count'] > max_count:
                yield 'npc', error

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

        def radius_pred(sq):
            """ Need for constraint of inflation of a wave """
            diff = sq[0] - pos[0], sq[1] - pos[1]
            if hypot(diff[0], diff[1]) > radius:
                return False
            return True

        st_a, end_a = angle - cone_angle / 2 , angle + cone_angle / 2
        def field_pred(sq):
            diff = sq[0] - pos[0], sq[1] - pos[1]
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
        field = sum(self.wave(pos, radius_pred), [])
        #TODO: optimize (limit wave by radius)
        return set(i for i in field if field_pred(i))

    def block(self, pos):
        assert self[pos] and pos not in self.blocked_squares
        self.blocked_squares.add(pos)

    def is_available(self, pos):
        return pos in self and pos not in self.blocked_squares

    def unblock(self, pos):
        self.blocked_squares.remove(pos)