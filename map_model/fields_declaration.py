
# maps kinds to dicts with fields
definition = {
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

npc = {
    'count': {
        'type': int
    },
    'model_name': {
        'type': str
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