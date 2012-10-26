import sys
from functools import wraps
from types import GeneratorType
from direct.interval.ActorInterval import ActorInterval
from direct.interval.LerpInterval import LerpNodePathInterval

_testing = False

def set_testing(value):
    global _testing
    _testing = value


def action(name):
    #TODO: refactor this hack using getattr in update_action
    actions = sys._getframe(1).f_locals['actions']
    assert name not in actions
    def wrapper(func):
        @wraps(func)
        def wrap(char, *args, **kwargs):
            assert char.action == None
            char.action = name
            gen = func(char, *args, **kwargs)
            assert isinstance(gen, GeneratorType)
            gen = _stack(gen)
            if _testing:
                return gen
            _runner(char, gen, None)
        actions[name] = wrap
        return wrap
    return wrapper


def _runner(char, gen, send_value=None):
    try:
        yielded = gen.send(send_value)
    except StopIteration:
        char.action = None
        return
    if isinstance(yielded, wait):
        def callback(task):
            _runner(char, gen)
        taskMgr.doMethodLater(yielded.seconds, callback, str(id(wait)))
    elif isinstance(yielded, (LerpNodePathInterval, ActorInterval)):
        def callback():
            _runner(char, gen)
        key = str(id(gen))
        base.acceptOnce(key, callback)
        yielded.setDoneEvent(key)
        yielded.start()
    elif isinstance(yielded, events):
        items = yielded.items
        def callback(e_name):
            for ev in items:
                base.ignore(ev)
            _runner(char, gen, e_name)
        for i in items:
            base.acceptOnce(i, callback, [i])
    else:
        raise Exception('Unsupported type ' + type(yielded).__name__)


def _stack(gen):
    stack = []
    cur_gen = gen
    send_value = None
    while True:
        try:
            yielded = cur_gen.send(send_value)
            if isinstance(yielded, GeneratorType):
                stack.append(cur_gen)
                cur_gen = yielded
                send_value = None
            elif isinstance(yielded, ret):
                if not stack:
                    raise Exception('Generator has not a parent')
                cur_gen = stack.pop()
                send_value = yielded.value
            else:
                send_value = yield yielded
        except StopIteration:
            if stack:
                cur_gen = stack.pop()
                send_value = None
            else:
                return


class ret:

    def __init__(self, val):
        self.value = val


class wait:

    def __init__(self, seconds):
        self.seconds = seconds


class events:

    def __init__(self, *items):
        self.items = items
