import sys
sys.path.insert(0, '')

import unittest
from map_model.map import Map, segment_crossing

class TestMap(unittest.TestCase):
    maxDiff = None

    def get_map(self, definitions, topology):
        data = dict(
            substrate_texture='grass',
            substrate_actions='free',
            action_groups={
                'walk':['walk', 'see'],
                'jump':['jump', 'see'],
                'free':['jump', 'walk', 'see']
            },
            definitions=definitions,
            topology=topology,
            start_position=(0, 0),
        )
        return Map(data=data, check=False)

    def test_wave(self):
        top = [
            'ss ss ss ss ss ss ss ss',
            'ss WL ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss',
            'ss ss st .. .. .. ss ss',
            'ss ss WL .. ss .. .. ss',
            'ss ss ss .. ss ss ss ss',
        ]

        defin = dict((i, {}) for i in ('WL', 'st'))
        map = self.get_map(defin, top)
        pred = lambda pos: map[pos].get('ident') != 'WL'
        waves = map.wave(map.groups['st'][0], pred)
        self.assertEqual([(2, 3), (3, 3), (1, 1), (1, 2), (1, 3)], next(waves))
        self.assertEqual([
            (2, 4), (3, 4), (4, 4), (4, 3),
            (2, 0), (1, 0), (0, 0), (0, 1),
            (0, 2), (0, 3), (0, 4)
        ] , next(waves))
        self.assertEqual([
            (2, 5), (3, 5), (1, 5),
            (4, 5), (5, 5), (5, 4),
            (5, 3), (0, 5)
        ], next(waves))

    def test_get_field_jump1(self):
        top = [
            'ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss',
            'ss ss st .. ss .. ss ss',
            'ss ss WL .. ss .. .. ss',
            'ss ss ss .. ss ss ss ss',
        ]

        defin = {'st':{}, 'WL': {'actions': 'walk'}}
        map = self.get_map(defin, top)
        field = list(map.get_jump_field(map.groups['st'][0]))
        self.assertEqual([(2, 4), (0, 2), (1, 3)], field)

    def test_get_field_jump2(self):
        top = [
            'ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss',
            'ss ss st .. .. .. ss ss',
            'ss ss WL .. ss .. .. ss',
            'ss ss ss .. ss ss ss ss',
        ]

        defin = {'st':{}, 'WL': {'actions': 'jump'}}
        map = self.get_map(defin, top)
        field = list(map.get_jump_field(map.groups['st'][0]))
        self.assertEqual([(2, 4), (2, 0), (1, 1), (0, 2), (1, 3)], field)

    def test_get_path(self):
        top = [
            'ss ss ss ss ss ss ss ss',
            'ss WL WL ss ss ss ss ss',
            'ss ss ss a7 a8 a9 b1 ss',
            'a4 a5 a6 ss .. .. ss b2',
            'a3 WL WL .. b7 ss .. b3',
            'a2 a1 st .. ss b6 b5 b4',
        ]

        steps = [i + str(n) for i in ('a', 'b')
                for n in range(1, 10)
                if not (i == 'b' and n > 7)]
        defin = dict((i, {}) for i in ['WL', 'st', 'fn'] + steps)
        map = self.get_map(defin, top)
        pred = lambda pos: map[pos].get('ident') != 'WL'
        res = map.get_path(map.groups['st'][0],
                                map.groups['b7'][0], pred)
        path = tuple(map.groups[i][0] for i in steps)
        self.assertEqual(path, res)

    def test_view_field1(self):
        top = [
            'ss fd fd fd fd fd fd fd ss',
            'ss ss fd fd fd fd fd ss ss',
            'ss ss ss fd fd fd ss ss ss',
            'ss ss ss ss st ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
        ]
        defin = {'st':{}, 'fd': {}}
        map = self.get_map(defin, top)
        pred = lambda x: True
        res = map.view_field(map.groups['st'][0], 90, 92, 10, pred)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_view_field2(self):
        top = [
            'ss ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
            'ss ss fd ss ss ss ss ss ss',
            'ss fd fd fd fd fd fd fd st',
            'ss ss fd ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
        ]
        defin = {'st':{}, 'fd': {}}
        map = self.get_map(defin, top)
        pred = lambda x: True
        res = map.view_field(map.groups['st'][0], 180, 20, 7, pred)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_view_field3(self):
        top = [
            'ss ss ss ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
            'ss ss ss fd fd fd ss ss ss',
            'st fd fd fd fd fd fd ss ss',
            'ss ss ss fd fd fd ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
        ]
        defin = {'st':{}, 'fd': {}}
        map = self.get_map(defin, top)
        pred = lambda x: True
        res = map.view_field(map.groups['st'][0], 0, 40, 6, pred)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_view_field4(self):
        top = [
            'st ss ss ss ss ss ss ss ss',
            'ss fd fd fd ss ss ss ss ss',
            'ss fd fd fd fd ss ss ss ss',
            'ss fd fd fd fd ss ss ss ss',
            'ss ss fd fd ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
        ]
        defin = {'st':{}, 'fd': {}}
        map = self.get_map(defin, top)
        pred = lambda x: True
        res = map.view_field(map.groups['st'][0], 315, 60, 5, pred)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_segment_crossing(self):
        segm1, segm2 = ((5, 3), (-1, 3)), ((2, 1), (2, 5))
        self.assertEqual((2, 3), segment_crossing(segm1, segm2))
        segm1, segm2 = ((7, 3), (2, 2)), ((2, 3), (7, 4))
        self.assertIsNone(segment_crossing(segm1, segm2))
        segm1, segm2 = ((3, 6), (2, 1)), ((2, 3), (5, 1))
        res = segment_crossing(segm1, segm2)
        self.assertEqual(2.35, round(res[0], 2))
        self.assertEqual(2.76, round(res[1], 2))
        segm1, segm2 = ((6, 1), (3, 3)), ((2, 1), (3, 6))
        self.assertIsNone(segment_crossing(segm1, segm2))
        segm1, segm2 = ((6, 1), (6, 8)), ((2, 2), (7, 3))
        res = segment_crossing(segm1, segm2)
        self.assertEqual(6, round(res[0], 2))
        self.assertEqual(2.8, round(res[1], 2))
        segm1, segm2 = ((6, 3), (6, 8)), ((2, 2), (7, 3))
        self.assertIsNone(segment_crossing(segm1, segm2))
        segm1, segm2 = ((-6, 8), (-6, 3)), ((-6, 11), (-6, 2))
        self.assertIsNone(segment_crossing(segm1, segm2))

    def test_view_field_with_obstacles1(self):
        top = [
            'ss ss ss ss st ss ss ss ss',
            'ss ss ss fd fd fd ss ss ss',
            'ss ss WL fd fd fd fd fd ss',
            'ss ss ss fd WL WL fd fd fd',
            'ss ss fd fd ss ss ss fd fd',
            'ss ss fd ss ss ss ss ss fd',
        ]
        defin = dict((i, {}) for i in ('WL', 'st', 'fd'))
        map = self.get_map(defin, top)
        pred = lambda pos: map[pos].get('ident') != 'WL'
        res = map.view_field(map.groups['st'][0], 270, 120, 7, pred)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_view_field_with_obstacles2(self):
        top = [
            'ss fd fd fd fd fd fd fd st',
            'ss ss fd fd fd fd fd fd fd',
            'ss ss fd fd fd fd ss WL fd',
            'ss ss fd fd fd ss ss ss fd',
            'ss ss ss fd ss ss ss ss fd',
            'ss ss ss ss ss ss ss ss fd',
        ]
        defin = dict((i, {}) for i in ('WL', 'st', 'fd'))
        map = self.get_map(defin, top)
        pred = lambda pos: map[pos].get('ident') != 'WL'
        res = map.view_field(map.groups['st'][0], 230, 120, 7, pred)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_get_radial_path(self):
        top = [
            'ss ss ss ss ss ss ss ss',
            'ss 55 ss .. ss ss ss ss',
            'ss ss to ss ss ss ss ss',
            'ss 44 44 cc fr ss ss ss',
            'ss ss 33 22 11 ss ss ss',
            'ss 33 ss 22 ss 11 ss ss',
        ]

        defin = dict((i, {}) for i in ('cc', 'fr', 'to', '11',
                                       '22', '33', '44', '55'))
        map = self.get_map(defin, top)
        pred = lambda pos: pos in map
        cc = map.groups['cc'][0]
        fr = map.groups['fr'][0]
        to = map.groups['to'][0]
        path = map.get_radial_path(cc, fr, to, pred, 2)
        self.assertEqual((
            ((4, 1), (5, 0)),
            ((3, 1), (3, 0)),
            ((2, 1), (1, 0)),
            ((2, 2), (1, 2)),
            ((2, 3), (1, 4))
        ), path)


if __name__ == '__main__':
    unittest.main()


