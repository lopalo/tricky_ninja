import os
os.environ["PANDA_PRC_DIR"] = os.getcwd()
os.environ["PANDA_PRC_PATH"] = os.getcwd()

import __builtin__
import cProfile
from direct.showbase.ShowBase import ShowBase
from manager import Manager
from settings import Settings
from misc.display_text import display_control_keys

class App(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        #TODO: implement main menu and selecting level (screenshot, title) from it
        self.set_manager('test_map.yaml')
        self.disableMouse()
        self.stop_loop = False
        base.accept(S.control_keys['close_window'], self.esc_handler)
        if S.show_control_keys:
            display_control_keys(S)

    def set_manager(self, *args, **kwargs):
        self.remove_manager()
        self.manager = Manager(*args, **kwargs)
        taskMgr.add(self.manager, 'manager')

    def remove_manager(self):
        if getattr(self, 'manager', None) is not None:
            taskMgr.remove('manager')
            self.manager.clear()
            self.manager = None

    def esc_handler(self):
        self.stop_loop = True

    def loop(self):
        while not self.stop_loop:
            taskMgr.step()


if __name__ == '__main__':
    __builtin__.S = Settings('settings.yaml')
    app = App()
    cProfile.run('app.loop()')