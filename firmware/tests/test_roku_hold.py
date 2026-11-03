# The Clonker 10000 -- Chapter 6 Roku ECP held-key experiment
# Copy to /tests/test_roku_hold.py on the Pico.
# Stop the Clonker main loop before running from REPL.
# Loading this file sends NO commands.
# A held key may change AVR volume continuously: start at a safe low level.

import time
from clonker import device_config_v2 as config
from clonker.net import http_transport

ROOM_ID = 'room-2'
MAX_HOLD_SECONDS = 2.0
KEYS = ('VolumeUp', 'VolumeDown')


def _endpoint():
    return config.current()['rooms'][ROOM_ID]['devices']['device-3']


def _send(kind, key):
    if kind not in ('keypress', 'keydown', 'keyup') or key not in KEYS:
        raise ValueError('Unsupported Roku key operation')
    path = '/{}/{}'.format(kind, key)
    t0 = time.monotonic()
    result = http_transport.send(_endpoint(), 'POST', path)
    print('{} {} -> HTTP {} in {:.1f} ms'.format(
        kind, key, result['status'], (time.monotonic() - t0) * 1000))
    return result


def release_all():
    """Best-effort cleanup. Call manually if an earlier run was interrupted."""
    for key in KEYS:
        try:
            _send('keyup', key)
        except Exception as exc:
            print('WARNING: release {} failed: {}'.format(key, repr(exc)))


def press(direction='up'):
    """Baseline: one complete Roku keypress."""
    key = _key(direction)
    return _send('keypress', key)


def _key(direction):
    if direction == 'up':
        return 'VolumeUp'
    if direction == 'down':
        return 'VolumeDown'
    raise ValueError('direction must be up or down')


def hold(direction='up', seconds=0.5):
    """Send keydown, wait, keyup. Observe real volume/repetition.

    The release is attempted in finally, even if the hold raises.
    Network failure or Ctrl-C can still prevent guaranteed delivery.
    """
    key = _key(direction)
    if not 0 <= seconds <= MAX_HOLD_SECONDS:
        raise ValueError('seconds must be 0..{}'.format(MAX_HOLD_SECONDS))
    print('HOLD {} for {:.2f} s'.format(key, seconds))
    try:
        _send('keydown', key)
        time.sleep(seconds)
    finally:
        try:
            _send('keyup', key)
        except Exception as exc:
            print('WARNING: release failed:', repr(exc))
            print('Run release_all() after connectivity is restored.')


def reverse(first='up', seconds=0.4):
    """Test explicit release before switching direction."""
    other = 'down' if first == 'up' else 'up'
    _key(first)
    if not 0 <= seconds <= MAX_HOLD_SECONDS:
        raise ValueError('Invalid hold duration')
    print('REVERSE {} -> {}'.format(first, other))
    try:
        hold(first, seconds)
        hold(other, seconds)
    finally:
        release_all()


def series(direction='up', durations=(0.2, 0.5, 1.0)):
    """Compare different hold lengths, one at a time; max three trials."""
    _key(direction)
    if not 1 <= len(durations) <= 3:
        raise ValueError('Use 1..3 durations')
    for duration in durations:
        hold(direction, duration)
        print('Observe volume; next test in 2 seconds (Ctrl-C to stop)')
        time.sleep(2)


print('Roku held-key experiment loaded. No commands sent.')
print('Start at safe volume. Try hold("up", 0.5) then hold("up", 1.0).')
print('For cleanup: release_all()')
