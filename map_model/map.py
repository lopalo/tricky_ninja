from math import atan2, hypot, degrees, sqrt
from heapq import heappush, heappop
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
        for num_row, row in enumerate(data['topology']):
            for index in range(0, len(data['topology'][0]), 3):
                ident = row[index:index+2]
                if ident == '..':
                    continue
                elif ident == 'ss':
                    info = dict(
                        kind='substrate_texture',
                        actions=data['substrate_actions']
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

    def wave(self, coord, pred=lambda x: True):
        assert self[coord], coord
        wave = [coord]
        visited = set(wave)
        while True:
            new_wave = []
            for c in wave:
                for n, info in self.neighbors(c, True):
                    if n not in visited and pred(n):
                        new_wave.append(n)
                        visited.add(n)
            if len(new_wave) == 0:
                return
            yield new_wave
            wave = new_wave

    def get_path(self, start, end, pred):
        open_lst = [(0 , 0, start)]
        visited = {start: None}
        while open_lst:
            cost, length, sq = heappop(open_lst)
            if sq == end:
                break
            for n, info in self.neighbors(sq, True):
                if n in visited or not pred(n):
                    continue
                is_corner = self.is_corner(sq, n)
                if is_corner and not self.is_free_corner(sq, n, pred):
                    continue
                step_length = sqrt(2) if is_corner else 1
                nlength = length + step_length
                cost = length + hypot(end[0] - n[0], end[1] - n[1])
                heappush(open_lst, (cost, length, n))
                visited[n] = sq
        if end not in visited:
            return
        parent = visited[end]
        path = [end]
        while parent is not None:
            path.append(parent)
            parent = visited[parent]
        path.reverse()
        return tuple(path[1:])

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
        assert self.is_corner(first, second), (first, second)
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

    def check_square(self, origin, target, pred):
        if pred(target):
            if not self.is_corner(origin, target):
                return True
            elif self.is_free_corner(origin, target, pred):
                return True
        return False

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
        return sum(self.wave(pos, field_pred), [])

    def block(self, pos):
        assert self[pos] and pos not in self.blocked_squares
        self.blocked_squares.add(pos)

    def is_available(self, pos):
        return pos in self and pos not in self.blocked_squares

    def unblock(self, pos):
        self.blocked_squares.remove(pos)

    def _get_line(self, fpos, spos):
        """ [start, end) """
        d = spos[0] - fpos[0], spos[1] - fpos[1]
        assert d[0] == d[1] or not d[0] or not d[1], (fpos, spos)
        cur_pos = fpos
        while cur_pos != spos:
            yield cur_pos
            x = cur_pos[0] + (d[0] / abs(d[0]) if d[0] else 0)
            y = cur_pos[1] + (d[1] / abs(d[1]) if d[1] else 0)
            cur_pos = x, y


    def get_radial_path(self, center_pos, from_pos, to_pos, pred, radius):
        assert from_pos != to_pos, (from_pos, to_pos)
        assert from_pos in self, from_pos
        f_rel_pos = from_pos[0] - center_pos[0], from_pos[1] - center_pos[1]
        t_rel_pos = to_pos[0] - center_pos[0], to_pos[1] - center_pos[1]
        rel_poses = deque(self._neighbors.values())
        for _ in range(len(rel_poses)):
            if rel_poses[0] == f_rel_pos:
                break
            rel_poses.rotate(1)
        start_rel = rel_poses.popleft()
        start_step = tuple((center_pos[0] + n * start_rel[0],
                            center_pos[1] + n * start_rel[1])
                            for n in range(1, radius + 1))
        first_path = []
        second_path = []
        for path in first_path, second_path:
            prev_step = start_step
            for rel_pos in rel_poses:
                rad_poses, prev_pos = [], center_pos
                for num in range(radius):
                    pos = prev_pos[0] + rel_pos[0], prev_pos[1] + rel_pos[1]
                    prev_step_pos = prev_step[num]
                    line = self._get_line(pos, prev_step_pos)
                    if all(pred(i) for i in line):
                        rad_poses.append(pos)
                    else:
                        break
                    prev_pos = pos
                if len(rad_poses) == radius:
                    path.append(rad_poses[0])
                else:
                    break
                if to_pos in path:
                    break
                prev_step = rad_poses
            rel_poses.reverse()
        first_path, second_path = tuple(first_path), tuple(second_path)
        if to_pos in first_path and to_pos in second_path:
            if len(first_path) < len(second_path):
                return first_path
            else:
                return second_path
        elif to_pos in first_path:
            return first_path
        elif to_pos in second_path:
            return second_path
        else:
            if len(first_path) > len(second_path):
                return first_path
            else:
                return second_path
