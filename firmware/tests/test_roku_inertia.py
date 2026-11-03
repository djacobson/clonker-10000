# The Clonker 10000 -- Chapter 6: simulated rotary / Roku hold experiment
# Copy to /tests/test_roku_inertia.py; stop main app before using REPL.
# Loading this file sends NO commands. No configuration is modified.
# CAUTION: Roku may repeat volume while held. Start at safe low volume.

import time
from clonker import device_config_v2 as config
from clonker.net import http_transport

ROOM_ID = 'room-2'
MAX_HOLD_S = 2.0       # absolute safety cap per hold, independent of detents
MAX_TEST_S = 8.0
KEYS = {'up': 'VolumeUp', 'down': 'VolumeDown'}


def _endpoint():
    return config.current()['rooms'][ROOM_ID]['devices']['device-3']


def _send(operation, direction):
    key = KEYS[direction]
    start = time.monotonic()
    result = http_transport.send(_endpoint(), 'POST',
                                 '/{}/{}'.format(operation, key))
    print('  {} {}: HTTP {} ({:.0f} ms)'.format(
        operation, direction, result['status'],
        (time.monotonic() - start) * 1000))


def release_all():
    """Best-effort emergency cleanup; call if a test was interrupted."""
    for direction in ('up', 'down'):
        try:
            _send('keyup', direction)
        except Exception as exc:
            print('  WARNING: release {} failed: {}'.format(direction, repr(exc)))


class HoldExperiment:
    def __init__(self, idle_ms=250):
        if not 50 <= idle_ms <= 1000:
            raise ValueError('idle_ms must be 50..1000')
        self.idle_s = idle_ms / 1000.0
        self.direction = None
        self.started = None
        self.last_detent = None
        self.detents = 0

    def stop(self):
        if self.direction is None:
            return
        direction = self.direction
        # Clear state first so repeated cleanup cannot extend a hold.
        self.direction = None
        self.started = None
        self.last_detent = None
        print('  RELEASE {}'.format(direction))
        _send('keyup', direction)

    def poll(self):
        if self.direction is None:
            return
        now = time.monotonic()
        if (now - self.last_detent >= self.idle_s or
                now - self.started >= MAX_HOLD_S):
            self.stop()

    def detent(self, direction):
        if direction not in KEYS:
            raise ValueError('direction must be up or down')
        self.poll()
        if self.direction is not None and self.direction != direction:
            self.stop()  # Must release previous direction before reversing.
        if self.direction is None:
            print('  START {}'.format(direction))
            _send('keydown', direction)
            self.started = time.monotonic()
            self.direction = direction
        else:
            print('  EXTEND {} (no HTTP)'.format(direction))
        self.last_detent = time.monotonic()
        self.detents += 1


def simulate(pattern='fast', idle_ms=250):
    """Run scheduled simulated detents; no physical encoder is read.

    fast:    8 up detents, 100 ms apart
    slow:    5 up detents, 400 ms apart
    reverse: 5 up detents then 4 down detents, 120 ms apart
    
    All events are scheduled by elapsed time. Blocking HTTP may delay
    their delivery; printed times show that distortion.
    """
    patterns = {
        'fast': [(i * 0.10, 'up') for i in range(8)],
        'slow': [(i * 0.40, 'up') for i in range(5)],
        'reverse': ([(i * 0.12, 'up') for i in range(5)] +
                    [(0.72 + i * 0.12, 'down') for i in range(4)]),
    }
    if pattern not in patterns:
        raise ValueError('pattern must be fast, slow, or reverse')
    controller = HoldExperiment(idle_ms)
    events = patterns[pattern]
    print('SIMULATE {} | idle={}ms | {} detents'.format(
        pattern, idle_ms, len(events)))
    start = time.monotonic()
    index = 0
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed > MAX_TEST_S:
                raise RuntimeError('test exceeded safety duration')
            controller.poll()
            if index < len(events) and elapsed >= events[index][0]:
                due, direction = events[index]
                print('  t={:.2f}s (scheduled {:.2f}s): detent {}'.format(
                    elapsed, due, direction))
                controller.detent(direction)
                index += 1
            if index == len(events) and controller.direction is None:
                break
            time.sleep(0.01)
        print('DONE: {} simulated detents; elapsed {:.2f}s'.format(
            controller.detents, time.monotonic() - start))
    finally:
        try:
            controller.stop()
        except Exception as exc:
            print('WARNING: stop failed:', repr(exc))
        # Always attempt both releases, including after a failed stop.
        release_all()


print('Roku simulated encoder test loaded; no commands sent.')
print('Start at safe volume: simulate("fast", 250)')
print('Other tests: simulate("slow", 250), simulate("reverse", 250)')
print('Emergency cleanup: release_all()')
