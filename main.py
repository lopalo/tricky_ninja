import __builtin__
from direct.showbase.ShowBase import ShowBase
from panda3d.core import ConfigVariableString
from manager import Manager
from settings import Settings

class App(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        #TODO: implement menu and setting manager from it
        self.set_manager('test_map.yaml')
        self.disableMouse()

    def set_manager(self, *args, **kwargs):
        self.remove_manager()
        self.manager = Manager(*args, **kwargs)
        taskMgr.add(self.manager, 'manager')

    def remove_manager(self):
        if getattr(self, 'manager', None) is not None:
            taskMgr.remove('manager')
            self.manager.clear()
            self.manager = None

if __name__ == '__main__':
    __builtin__.S = Settings('settings.yaml')
    ConfigVariableString("show-frame-rate-meter").setValue('#t')
    app = App()
    run()