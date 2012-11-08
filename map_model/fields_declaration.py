from os import path

# maps kinds to dicts with fields
def get_definition():
    #TODO: fields with material properties
    definition = {
        'empty': {},
        'model_field': {
            '_no_actions': True,
            'group': {
                'type': str
            },
        },
        'texture': {
            'texture': {
                'type': str,
                'variants_dir': path.join(S._path, S.paths['map_textures'])
            },
        },
        'model': {
            'model': {
                'type' : str,
                'variants_dir': path.join(S._path, S.paths['models'])
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
                'type': str,
                'variants_dir': path.join(S._path, S.paths['models'])
            },
            'left_bottom_model': {
                'type': str,
                'variants_dir': path.join(S._path, S.paths['models'])
            },
        },
        'sprite': {
            'texture': {
                'type': str,
                'variants_dir': path.join(S._path, S.paths['textures'])
            },
            'size': {
                'type': float,
                'default': True,
                'positive': True,
            }
        }
    }
    return definition

npc = {
    'count': {
        'type': int
    },
    'texture': {
        'type': str
    },
    'alert_texture': {
        'type': str,
        'default': True,
    },
    'route': {
        'type': str,
    },
}