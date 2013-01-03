import os
os.environ["PANDA_PRC_DIR"] = os.getcwd()
os.environ["PANDA_PRC_PATH"] = os.getcwd()

import __builtin__
import cProfile
from glob import glob
from collections import deque
import yaml
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import *
from panda3d.core import *
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from manager import Manager
from settings import Settings
from misc.display_text import display_control_keys

class App(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        self._setup_menu()
        self.disableMouse()
        self.stop_loop = False
        self.loading = False
        base.accept(S.control_keys['close_window'], self.esc_handler)
        if S.show_control_keys:
            display_control_keys(S)

    def _load_map_infos(self):
        for fname in sorted(glob(os.path.join(S.map_dir, '*.yaml'))):
            with open(fname, 'r') as f:
                map_data = yaml.load(f)
            title = map_data.get('title', 'unnamed').capitalize()
            ident = os.path.basename(fname)
            thumbnail = S.map_thumbnail(map_data.get('thumbnail', 'unknown'))
            yield dict(title=title,
                       thumbnail=thumbnail,
                       ident=ident)

    def _setup_menu(self):
        parent = render2d.attachNewNode(PGTop('menu_node'))
        parent.node().setMouseWatcher(base.mouseWatcherNode)

        OnscreenImage(image=S.menu_backg, scale=(1, 1, 1)).reparentTo(parent)
        def start():
            if self.loading:
                return
            self.loading = True
            parent.removeNode()
            self.set_manager(self.map_infos[0]['ident'])
        DirectButton(command=start,
                     text='Start',
                     borderWidth=(0, 0),
                     frameColor=(1, 1, 1, 1),
                     pos=(0, 0, -0.4),
                     scale=0.1).reparentTo(parent)
        self._make_exit_button(parent)
        self.map_infos = map_infos = deque(self._load_map_infos())
        self.map_thumbnail = OnscreenImage(image=map_infos[0]['thumbnail'],
                                           scale=0.3)
        self.map_thumbnail.reparentTo(parent)
        self.map_title = OnscreenText(text=map_infos[0]['title'],
                                      pos=(0, 0.35),
                                      fg=(1, 1, 1, 1),
                                      scale = 0.05)
        self.map_title.reparentTo(parent)
        self._make_switch_button(True, parent)
        self._make_switch_button(False, parent)

    def _make_switch_button(self, right, parent):
        def switch():
            self.map_infos.rotate(-1 if right else 1)
            self.map_thumbnail.setImage(self.map_infos[0]['thumbnail'])
            self.map_title.setText(self.map_infos[0]['title'])
        DirectButton(command=switch,
                     text='>' if right else '<',
                     borderWidth=(0, 0),
                     frameColor=(1, 1, 1, 1),
                     pos=(0.4 if right else -0.4, 0, 0),
                     scale=0.1).reparentTo(parent)

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
                             text="Do you want to exit?",
                             command=handler)

    def loop(self):
        while not self.stop_loop:
            taskMgr.step()


if __name__ == '__main__':
    __builtin__.S = Settings('settings.yaml')
    app = App()
    cProfile.run('app.loop()')


