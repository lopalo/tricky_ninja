import sys
sys.path.insert(0, '')

import unittest
from map import Map

class TestMap(unittest.TestCase):

    def get_map(self, definitions, topology):
        data = dict(
            substrate_texture='grass',
            substrate_actions='free',
            action_groups={
                'walk':['walk'],
                'jump':['jump'],
                'free':['jump', 'walk']
            },
            definitions=definitions,
            topology=topology
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
        self.assertEqual([(2, 3), (1, 2), (1, 3)], next(waves))
        self.assertEqual([
            (2, 4), (3, 3), (3, 4),
            (1, 1), (0, 2), (0, 1),
            (0, 3)
        ], next(waves))
        self.assertEqual([
            (2, 5), (3, 5), (4, 3),
            (4, 4), (4, 5), (1, 0),
            (0, 0), (0, 4)
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
            'ss a5 a6 a7 a8 a9 b1 ss',
            'a4 ss ss ss .. .. ss b2',
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
        res = map.view_field(map.groups['st'][0], 90, 92, 10, None)
        self.assertItemsEqual(map.groups['fd'], res)

    def test_view_field2(self):
        top = [
            'ss ss ss ss st ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
            'ss ss fd ss ss ss ss ss ss',
            'ss fd fd fd fd fd fd fd st',
            'ss ss fd ss ss ss ss ss ss',
            'ss ss ss ss ss ss ss ss ss',
        ]
        defin = {'st':{}, 'fd': {}}
        map = self.get_map(defin, top)
        res = map.view_field(map.groups['st'][0], 180, 20, 7, None)
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
        res = map.view_field(map.groups['st'][0], 0, 40, 6, None)
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
        res = map.view_field(map.groups['st'][0], 315, 60, 5, None)
        self.assertItemsEqual(map.groups['fd'], res)

if __name__ == '__main__':
    unittest.main()


