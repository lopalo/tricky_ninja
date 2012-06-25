import os
import yaml

class Settings(object):

    def __init__(self, path):
        with open(path, 'r') as f:
            data = yaml.load(f)
        self.__dict__.update(data)
        self._path = os.path.dirname(__file__)
        path = os.path.join(self._path, self.paths['model_sizes'])
        with open(path, 'r') as f:
            self.model_sizes = yaml.load(f)
        self.pl_anim = self.player['animation']
        self.npc_anim = self.player['animation']
        self.ch_anim = self.character['animation']

    def map_texture(self, name):
        #returns directory
        return os.path.join(self._path, self.paths['map_textures'], name)

    def texture(self, name):
        name += '.png'
        return os.path.join(self._path, self.paths['textures'], name)

    def model(self, name):
        return os.path.join(self._path, self.paths['models'], name)

    def map(self, name):
        return os.path.join(self._path, self.paths['maps'], name)

    def model_size(self, model_name):
        return self.model_sizes.get(model_name, 1)
