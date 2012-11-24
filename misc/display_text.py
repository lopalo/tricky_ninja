from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

def display_control_keys(settings):
    scale = settings.text_scale
    keys = (tuple(i.items())[0] for i in settings.ordered_control_keys)
    for row, (action, key) in enumerate(keys, 1):
        text = action.replace('_', ' ') + ': ' + key
        OnscreenText(style=1,
                     text=text,
                     fg=(1, 1, 1, 1),
                     pos=(-1, 1 - (scale * row)),
                     align=TextNode.ALeft,
                     scale=scale).reparentTo(render2d)