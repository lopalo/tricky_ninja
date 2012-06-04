import os
import yaml

class Settings(object):

    def __init__(self, path):
        with open(path, 'r') as f:
            data = yaml.load(f)
        self.__dict__.update(data)
        self.paths = data['paths']

    def texture(self, name):
        return os.path.join(self.paths['textures'], name)

    def model(self, name):
        return os.path.join(self.paths['models'], name)

    def map(self, name):
        return os.path.join(self.paths['maps'], name)