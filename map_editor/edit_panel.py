from os.path import basename
from glob import glob
from direct.gui.DirectGui import *
from panda3d.core import *
from map_model.fields_declaration import get_definition, AVAILABLE_ACTIONS

class EditPanel:

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
        self._add_row('group_selection_title', label('group:'))
        self._group_selection = GroupSelection(self)
        self._add_row('group_selection', self._group_selection.widget)

    def _add_row(self, name, widget, set_titile=True):
        self._widgets.append((name, widget))
        widget.reparentTo(self.frame)
        if isinstance(widget, (DirectLabel, DirectCheckButton)):
            x = -(1 - ES.border) / 2
        else:
            x = -(1 - ES.border - ES.edit_panel['left_margin'])
        pos = (x, 0, -0.1 - self._row_count * ES.edit_panel['row_height'])
        widget.setPos(pos)
        self._row_count += 1

    def _delete_until(self, name):
        for n, widget in tuple(reversed(self._widgets)):
            if n == name:
                return
            self._widgets.pop()
            widget.destroy()
            self._row_count -= 1

    def set_current_group(self, group_id):
        self._delete_until('group_selection')
        group = self.all_groups[group_id] if group_id else None
        self.editor.set_current_group(group)
        if group_id not in (None, 'ss'):
            self._add_row('kind_selection_title', label('kind:'))
            self._add_row('kind_selection', kind_widget(self))
            self.set_group_by_kind()

    def set_group_by_kind(self):
        self._delete_until('kind_selection')
        group = self.editor.current_group
        kind = group.get('kind')
        fields = get_definition()[kind]
        for fname, info in fields.items():
            if fname.startswith('_'):
                continue
            self._add_row(fname + '_title', label(fname + ':'))
            if fname == 'group':
                self._add_row(fname, group_widget(self, fname, **info))
            elif 'variants_dir' in info:
                self._add_row(fname, combobox_widget(self, fname, **info))
            else:
                self._add_row(fname, row_widget(self, fname, **info))
        if not fields.get('_no_actions', False):
            self._add_row('actions_title', label('actions:'))
            for action in AVAILABLE_ACTIONS:
                widget = action_widget(self, 'actions', action)
                self._add_row('action_' + action, widget)
        self.editor.map_builder.redraw_group(group['ident'])


    def select_group(self, ident):
        self._group_selection.set(ident)

    def add_group(self, ident):
        self._group_selection.append(ident)


class GroupSelection:
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

    def append(self, group_id):
        items = self.items
        items.append(group_id)
        self.widget['items'] = items
        self.set_value(items[0])


### widgets makers ###

def label(text):
    return DirectLabel(text=text, scale=ES.edit_panel['widget_scale'])


def kind_widget(edit_panel):
    group = edit_panel.editor.current_group
    items = sorted(get_definition())
    init_item = items.index(group['kind'])

    def set_value(kind):
        definition = get_definition()
        old_kind = group.get('kind')
        if old_kind is not None:
            fields = definition[old_kind]
            for fname in fields:
                if fname.startswith('_'):
                    continue
                group.pop(fname, None)
        group['kind'] = kind
        for fname, info in definition[kind].items():
            if fname.startswith('_'):
                    continue
            if info.get('default', False):
                continue
            group[fname] = info['type']()
        edit_panel.set_group_by_kind()

    return DirectOptionMenu(highlightColor=(0.6, 0.6, 0.6, 1),
                            command=set_value,
                            items=items,
                            initialitem=init_item,
                            borderWidth=(0.05, 0.05),
                            scale=ES.edit_panel['widget_scale'],
                            sortOrder=1)


def combobox_widget(edit_panel, fname, type, variants_dir, **kwargs):
    """Cannot contain empty value"""

    group = edit_panel.editor.current_group
    items = [basename(i).split('.')[0] for i
                in glob(variants_dir + '/*[!~]')]
    if 'textures' in items:
        items.remove('textures') # ignore textures of models
    if group[fname] in items:
        init_item = items.index(group[fname])
    else:
        init_item = None
    if init_item is None:
        group[fname] = type(items[0])

    def set_value(value):
        group[fname] = type(value)
        edit_panel.editor.map_builder.redraw_group(group['ident'])

    return DirectOptionMenu(highlightColor=(0.6, 0.6, 0.6, 1),
                            command=set_value,
                            items=items,
                            initialitem=init_item or 0,
                            borderWidth=(0.05, 0.05),
                            scale=ES.edit_panel['widget_scale'],
                            sortOrder=1)


def row_widget(edit_panel, fname, type, default=False, **kwargs):
    group = edit_panel.editor.current_group

    def change_text(text):
        if not text and default:
            group.pop(fname, None)
        else:
            try:
                group[fname] = type(text)
            except ValueError:
                pass
        edit_panel.editor.map_builder.redraw_group(group['ident'])

    def focus_in():
        edit_panel.editor.remove_arrow_handlers()

    def focus_out():
        edit_panel.editor.set_camera_control(only_arrows=True)

    return DirectEntry(command=change_text,
                       focusInCommand=focus_in,
                       focusOutCommand=focus_out,
                       initialText=str(group.get(fname, '')),
                       numLines=1,
                       width=ES.edit_panel['row_width'],
                       frameColor=(1, 1, 1, 1),
                       scale=ES.edit_panel['widget_scale'] / 2,
                       focus=0)


def group_widget(edit_panel, fname, type, **kwargs):
    """Cannot contain empty value"""

    group = edit_panel.editor.current_group
    items = sorted(edit_panel.all_groups)
    if group[fname] in items:
        init_item = items.index(group[fname])
    else:
        init_item = None

    if init_item is None:
        group[fname] = type(items[0])

    def set_value(value):
        group[fname] = type(value)

    return DirectOptionMenu(highlightColor=(0.6, 0.6, 0.6, 1),
                            command=set_value,
                            items=items,
                            initialitem=init_item or 0,
                            borderWidth=(0.05, 0.05),
                            scale=ES.edit_panel['widget_scale'],
                            sortOrder=1)


def action_widget(edit_panel, fname, action):
    actions = edit_panel.editor.current_group[fname]

    def set_value(status):
        if status:
            actions.append(action)
        else:
            actions.remove(action)

    return DirectCheckButton(command=set_value,
                             text=action,
                             indicatorValue=action in actions,
                             scale=ES.edit_panel['widget_scale'])
