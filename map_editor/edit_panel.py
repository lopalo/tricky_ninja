from direct.gui.DirectGui import *

class EditPanel:

    def __init__(self, editor):
        self.editor = editor
        fsize = (-(1 - ES.border), 0, -2, 0)
        self.frame = frame = DirectFrame(frameSize=fsize, pos=(1, 0, 1))
        frame.reparentTo(render2d)
        frame.setBin('fixed', 10)