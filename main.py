import os
os.environ["PANDA_PRC_DIR"] = os.getcwd()
os.environ["PANDA_PRC_PATH"] = os.getcwd()

import __builtin__
import cProfile
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import *
from panda3d.core import *
from direct.gui.OnscreenImage import OnscreenImage
from manager import Manager
from settings import Settings
from misc.display_text import display_control_keys

class App(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        #TODO: implement main menu and selecting level (screenshot, title) from it

        self._setup_menu()
        self.disableMouse()
        self.stop_loop = False
        self.loading = False
        base.accept(S.control_keys['close_window'], self.esc_handler)
        if S.show_control_keys:
            display_control_keys(S)

    def _setup_menu(self):
        parent = render2d.attachNewNode(PGTop('menu_node'))
        parent.node().setMouseWatcher(base.mouseWatcherNode)

        OnscreenImage(image=S.menu_backg, scale=(1, 1, 1)).reparentTo(parent)
        def start():
            if self.loading:
                return
            self.loading = True
            parent.removeNode()
            self.set_manager('bigmap.yaml')
        DirectButton(command=start,
                     text='Start',
                     borderWidth=(0, 0),
                     frameColor=(1, 1, 1, 1),
                     pos=(0, 0, -0.4),
                     scale=0.1).reparentTo(parent)
        self._make_exit_button(parent)

    def _make_exit_button(self, parent):
        def exit():
            self.stop_loop = True
        DirectButton(command=exit,
                    text='Exit',
                    borderWidth=(0, 0),
                    frameColor=(1, 1, 1, 1),
                    pos=(0, 0, -0.52),
                    scale=0.1).reparentTo(parent)

    def set_manager(self, *args, **kwargs):
        preloader = OnscreenImage(image=S.preloader, scale=(1, 1, 1))
        preloader.reparentTo(render2d)
        def callback(task):
            self.manager = Manager(*args, **kwargs)
            taskMgr.add(self.manager, 'manager')
            preloader.destroy()
        taskMgr.doMethodLater(0.1, callback, 'set_manager')

    def finish_game(self, win):
        taskMgr.remove('manager')
        parent = render2d.attachNewNode(PGTop('finish_node'))
        parent.node().setMouseWatcher(base.mouseWatcherNode)
        backg = S.win_backg if win else S.fail_backg
        OnscreenImage(image=backg, scale=(1, 1, 1)).reparentTo(parent)
        self._make_exit_button(parent)

    def esc_handler(self):
        def handler(yes):
            if yes:
                self.stop_loop = True
            else:
                dialog.cleanup()
        dialog = YesNoDialog(dialogName="ExitDialog",
                             text="Do you want exit?",
                             command=handler)

    def loop(self):
        while not self.stop_loop:
            taskMgr.step()


if __name__ == '__main__':
    __builtin__.S = Settings('settings.yaml')
    app = App()
    cProfile.run('app.loop()')