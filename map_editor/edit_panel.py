from os.path import basename
from glob import glob
from direct.gui.DirectGui import *
from panda3d.core import *
from map_model.fields_declaration import get_definition

class EditPanel:
    #TODO: adding new group that should be in map dedinitions and map groups

    def __init__(self, editor):
        self._row_count = 0
        self._widgets = []
        self.editor = editor
        self.all_groups = editor.map.definitions
        fsize = (-(1 - ES.border), 0, -2, 0)
        self.frame = DirectFrame(frameSize=fsize, pos=(1, 0, 1), sortOrder=0)
        self.node = render2d.attachNewNode(PGTop('panel_node'))
        self.node.node().setMouseWatcher(base.mouseWatcherNode)
        self.frame.reparentTo(self.node)
        self._add_row('group_selection_title', Label('group:'))
        self._add_row('group_selection', SelectGroupWidget(self))

    def _add_row(self, name, obj, set_titile=True):
        setattr(self, '_' + name, obj)
        self._widgets.append((name, obj))
        obj.widget.reparentTo(self.frame)
        if isinstance(obj, Label):
            x = -(1 - ES.border) / 2
        else:
            x = -(1 - ES.border - ES.edit_panel['left_margin'])
        pos = (x, 0, -0.1 - self._row_count * ES.edit_panel['row_height'])
        obj.widget.setPos(pos)
        self._row_count += 1

    def _delete_until(self, name):
        for n, obj in tuple(reversed(self._widgets)):
            if n == name:
                return
            self._widgets.pop()
            obj.widget.destroy()
            self._row_count -= 1

    def set_current_group(self, group_id):
        self._delete_until('group_selection')
        group = self.all_groups[group_id] if group_id else None
        self.editor.set_current_group(group)
        if group_id not in(None, 'ss'):
            self._add_row('kind_selection_title', Label('kind:'))
            self._add_row('kind_selection', SelectKindWidget(self))
            self.set_group_by_kind()

    def set_group_by_kind(self):
        self._delete_until('kind_selection')
        group = self.editor.current_group
        kind = group.get('kind')
        if kind is not None:
            fields = get_definition()[kind]
            for fname, info in fields.items():
                self._add_row(fname + '_title', Label(fname + ':'))
                if 'variants_dir' in info:
                    self._add_row(fname, ComboboxWidget(self, fname, **info))
                else:
                    self._add_row(fname, RowWidget(self, fname, **info))
        #TODO: set actions widget
        self.editor.map_builder.redraw_group(group['ident'])


    def select_group(self, ident):
        self._group_selection.set(ident)


class Label:

    def __init__(self, text):
        self.widget = DirectLabel(text=text,
                                  scale=ES.edit_panel['widget_scale'])


class SelectGroupWidget:
    """ Should be created once when editor is loaded and current group is None"""

    def __init__(self, edit_panel):
        self.edit_panel = edit_panel
        self.items = [''] + sorted(edit_panel.all_groups)
        self.widget = DirectOptionMenu(highlightColor=(0.6, 0.6, 0.6, 1),
                                       command=self.set_value,
                                       items=self.items,
                                       initialitem=0,
                                       borderWidth=(0.05, 0.05),
                                       scale=ES.edit_panel['widget_scale'],
                                       sortOrder=1)

    def set(self, group_id):
        if group_id is None:
            group_id = ''
        self.widget.set(self.items.index(group_id))

    def set_value(self, group_id):
        self.edit_panel.set_current_group(group_id or None)

    #TODO: append to list new group


class SelectKindWidget:

    def __init__(self, edit_panel):
        self.edit_panel = edit_panel
        self.group = edit_panel.editor.current_group
        self.items = sorted(get_definition())
        init_item = self.items.index(self.group['kind'])
        self.widget = DirectOptionMenu(highlightColor=(0.6, 0.6, 0.6, 1),
                                       command=self.set_value,
                                       items=self.items,
                                       initialitem=init_item,
                                       borderWidth=(0.05, 0.05),
                                       scale=ES.edit_panel['widget_scale'],
                                       sortOrder=1)

    def set_value(self, kind):
        definition = get_definition()
        old_kind = self.group.get('kind')
        if old_kind is not None:
            fields = definition[old_kind]
            for fname in fields:
                self.group.pop(fname, None)
        self.group['kind'] = kind
        for fname, info in definition[kind].items():
            if info.get('default', False):
                continue
            self.group[fname] = info['type']()
        self.edit_panel.set_group_by_kind()


class ComboboxWidget:
    """Cannot contain empty value"""

    def __init__(self, edit_panel, fname, type, variants_dir, **kwargs):
        self.edit_panel = edit_panel
        self.group = edit_panel.editor.current_group
        self.fname = fname
        self.type = type
        items = [basename(i).split('.')[0] for i
                    in glob(variants_dir + '/*[!~]')]
        items.remove('textures') # ignore textures of models
        if self.group[fname] in items:
            init_item = items.index(self.group[fname])
        else:
            init_item = None
        self.widget = DirectOptionMenu(highlightColor=(0.6, 0.6, 0.6, 1),
                                       command=self.set_value,
                                       items=items,
                                       initialitem=init_item or 0,
                                       borderWidth=(0.05, 0.05),
                                       scale=ES.edit_panel['widget_scale'],
                                       sortOrder=1)
        if init_item is None:
            self.group[self.fname] = self.type(items[0])

    def set_value(self, value):
        self.group[self.fname] = self.type(value)
        self.edit_panel.editor.map_builder.redraw_group(self.group['ident'])


class RowWidget:

    def __init__(self, edit_panel, fname, type, default=False, **kwargs):
        self.edit_panel = edit_panel
        self.group = edit_panel.editor.current_group
        self.fname = fname
        self.type = type
        self.default = default
        self.widget = DirectEntry(command=self.change_text,
                                  focusInCommand=self.focus_in,
                                  focusOutCommand=self.focus_out,
                                  initialText=str(self.group.get(fname, '')),
                                  numLines=1,
                                  width=ES.edit_panel['row_width'],
                                  frameColor=(1, 1, 1, 1),
                                  scale=ES.edit_panel['widget_scale'] / 2,
                                  focus=0)

    def change_text(self, text):
        if not text and self.default:
            self.group.pop(self.fname, None)
        else:
            self.group[self.fname] = self.type(text)
        self.edit_panel.editor.map_builder.redraw_group(self.group['ident'])

    def focus_in(self):
        self.edit_panel.editor.remove_arrow_handlers()

    def focus_out(self):
        self.edit_panel.editor.set_camera_control(only_arrows=True)

