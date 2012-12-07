from uuid import uuid4
from functools import wraps
from types import GeneratorType
from direct.interval.ActorInterval import ActorInterval
from direct.interval.LerpInterval import LerpNodePathInterval

_testing = False

def set_testing(value):
    global _testing
    _testing = value


def action(func):
    fname = func.__name__
    assert fname.startswith('do_')
    name = fname[3:]
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
    return wrap


def _runner(char, gen, send_value=None):
    try:
        yielded = gen.send(send_value)
    except StopIteration:
        char.action = None
        return
    key = uuid4().hex

    def timeout_handler(task):
        if key not in char.action_timeouts:
            return
        char.action_timeouts.remove(key)
        _runner(char, gen)

    if isinstance(yielded, wait):
        def callback(task):
            _runner(char, gen)
        taskMgr.doMethodLater(yielded.seconds, callback, key)
    elif isinstance(yielded, (LerpNodePathInterval, ActorInterval)):
        def callback():
            if key not in char.action_timeouts:
                return
            char.action_timeouts.remove(key)
            _runner(char, gen)
        char.action_timeouts.append(key)
        base.acceptOnce(key, callback)
        yielded.setDoneEvent(key) # sometimes doesn't emit; fixed by timeout
        timeout = yielded.getDuration() + S.character['resume_action_timeout']
        taskMgr.doMethodLater(timeout, timeout_handler, key + '_timeout')
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
