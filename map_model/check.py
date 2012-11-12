from map_model import fields_declaration as fdecl


class MapDataError(Exception):
    pass


def check_map_data(data):
    group_definition = fdecl.get_definition()
    all_actions = set(fdecl.AVAILABLE_ACTIONS)
    stop = False
    for f in ('substrate_texture', 'definitions',
              'topology', 'start_position', 'hour'):
        if f not in data:
            stop = True
            yield f, 'is not specified'
    if stop: return
    if type(data['substrate_texture']) is not str:
        yield 'substrate_texture', 'is not a string'
    actions = set(data.get('substrate_actions', []))
    if actions - all_actions:
            yield ('substrate_actions', "unknown action")
    for id, info in data['definitions'].items():
        if len(id) != 2:
            yield ('definitions',
                "ident '{0}' should contain two characters".format(id))
        for row in data['topology']:
            if id in row:
                break
        else:
            yield 'definitions', "'{0}' is not in topology".format(id)
        actions = set(info.get('actions', []))
        if actions - all_actions:
            yield ('definitions', "unknown action for '{0}'".format(id))
        kind = info.get('kind', 'empty')
        if kind not in group_definition:
            yield 'definitions', "unknown kind for '{0}'".format(id)
            continue
        fields = group_definition[kind]
        for f, i in fields.items():
            if f.startswith('_'):
                continue
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
            if f == 'group' and info['group'] not in data['definitions']:
                yield ('definitions',
                "field 'group' of '{0}' has unknown group ident".format(id))

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
