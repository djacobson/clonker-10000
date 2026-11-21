# The Clonker 10000
# firmware/tests/test_wifi_info.py
# Read-only CircuitPython Wi-Fi association diagnostic.
# No scans, reconnects, socket operations, or filesystem writes.

import wifi


def show(label, getter):
    try:
        value = getter()
        if value is None:
            value = '(unavailable)'
        print('{:<18} {}'.format(label + ':', value))
    except Exception as exc:
        print('{:<18} {}: {}'.format(label + ':', type(exc).__name__, exc))


def mac_text(value):
    if value is None:
        return '(unavailable)'
    if isinstance(value, (bytes, bytearray)):
        return ':'.join('{:02X}'.format(b) for b in value)
    return str(value)


print('\n=== CLONKER WIFI INFO (READ ONLY) ===')
radio = wifi.radio
show('Connected', lambda: radio.connected)
show('IPv4 address', lambda: radio.ipv4_address)
show('IPv4 gateway', lambda: radio.ipv4_gateway)
show('IPv4 subnet', lambda: radio.ipv4_subnet)
show('Radio MAC', lambda: mac_text(radio.mac_address))

try:
    ap = radio.ap_info
except Exception as exc:
    ap = None
    print('AP info error: {}: {}'.format(type(exc).__name__, exc))

if ap is None:
    print('Associated AP:     (unavailable)')
else:
    show('AP SSID', lambda: ap.ssid)
    show('AP BSSID', lambda: mac_text(ap.bssid))
    show('AP channel', lambda: ap.channel)
    show('AP RSSI (dBm)', lambda: ap.rssi)
    show('AP authmode', lambda: ap.authmode)

print('=== END WIFI INFO ===\n')
