from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

def display_control_keys(settings):
    SCALE = .03

    keys = (tuple(i.items())[0] for i in settings.ordered_control_keys)
    for row, (action, key) in enumerate(keys, 1):
        text = action.replace('_', ' ') + ': ' + key
        OnscreenText(style=1,
                     text=text,
                     fg=(1, 1, 1, 1),
                     pos=(-1, 1 - (SCALE * row)),
                     align=TextNode.ALeft,
                     scale = SCALE).reparentTo(render2d)