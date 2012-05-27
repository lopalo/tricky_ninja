import yaml

class MapDataError(Exception):
    pass

class Map(object):

    def __init__(self, manager, name):
        with open(S.map(name), 'r') as f:
           data = yaml.load(f)
           data['topology'].reverse()
        try:
            self._check_data(data)
        except AssertionError as e:
            raise MapDataError(e.message)
        self.substrate_texture = data['substrate-texture']
        self.data = {}
        for num_row, row in enumerate(data['topology']):
            for index in range(0, len(data['topology'][0]), 2):
                ident = row[index:index+2]
                if ident == '..':
                    continue
                elif ident == 'ss':
                    info = dict(kind='substrate_texture')
                else:
                    info = data['definitions'][ident]
                    info['ident'] = ident
                self.data[index/2, num_row] = info

    def _check_data(self, data):
        pass

    def __getitem__(self, val):
        return self.data.get(val)

    def __iter__(self):
        return self.data.items().__iter__()