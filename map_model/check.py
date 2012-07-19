from map_model import fields_declaration as fdecl


AVAILABLE_ACTIONS = ('walk', 'jump', 'see')


class MapDataError(Exception):
    pass


def check_map_data(data):
    stop = False
    for f in ('substrate_texture', 'definitions',
              'topology', 'action_groups'):
        if f not in data:
            stop = True
            yield f, 'is not specified'
    if stop: return
    if type(data['substrate_texture']) is not str:
        yield 'substrate_texture', 'is not a string'
    actions = data['substrate_actions']
    if actions is not None and actions not in data['action_groups']:
            yield ('substrate_actions', "unknown action group")
    for id, info in data['definitions'].items():
        if len(id) != 2:
            yield ('definitions',
                "ident '{0}' should contain two characters".format(id))
        for row in data['topology']:
            if id in row:
                break
        else:
            yield 'definitions', "'{0}' is not in topology".format(id)
        actions = info.get('actions')
        if actions is not None and actions not in data['action_groups']:
            yield ('definitions',
                    "unknown action group for '{0}'".format(id))
        kind = info.get('kind')
        if kind is None:
            continue
        elif kind not in fdecl.definition:
            yield 'definitions', "unknown kind for '{0}'".format(id)
            continue
        fields = fdecl.definition[kind]
        for f, i in fields.items():
            if not i.get('default', False) and f not in info:
                yield ('definitions',
                "value of '{0}' doesn't contain '{1}' field".format(id, f))
            if f not in info:
                continue
            if not isinstance(info[f], i['type']):
                t_name = i['type'].__name__
                yield ('definitions',
                "field '{0}' of '{1}' is not {2}".format(f, id, t_name))
            if i.get('positive') and info[f] <= 0:
                yield ('definitions',
                "field '{0}' of '{1}' must be positive".format(f, id))

    length = len(data['topology'][0])
    for row in data['topology']:
        if (len(row) + 1) % 3:
            yield 'topology', 'wrong length of row'
        if len(row) != length:
            yield 'topology', 'different count of rows'
        for index in range(0, length, 3):
            id = row[index:index+2]
            if id in ('..', 'ss'):
                continue
            if id not in data['definitions']:
                yield 'topology', 'unknown ident ' + id

    used_action_groups = set(i['actions'] for i in
                             data['definitions'].values()
                             if i.get('actions') is not None)
    unused = set(data['action_groups']) - used_action_groups
    if unused:
        yield 'action_groups', 'Unused groups ' + str(list(unused))
    for k, v in data['action_groups'].items():
        for a in v:
            if a not in AVAILABLE_ACTIONS:
                yield ('action_groups',
                    "'{0}' contains unknown action".format(k))

    for num, npc in enumerate(data.get('npcs', tuple())):
        for f, i in fdecl.npc.items():
            if not i.get('default', False) and f not in npc:
                yield ('npc',
                "{0}: doesn't contain '{1}' field".format(num, f))
            if f not in npc:
                continue
            if not isinstance(npc[f], i['type']):
                t_name = i['type'].__name__
                yield ('npc',
                "{0}: field '{1}' is not {2}".format(num, f, t_name))
            if f == 'route' and npc[f] not in data.get('routes', tuple()):
                yield 'npc', '{0}: unknown route'.format(num)
