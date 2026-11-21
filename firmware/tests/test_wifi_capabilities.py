# THE CLONKER 10000 - standalone Wi-Fi capability / scan test
# CircuitPython 10.3.1, Raspberry Pi Pico 2 W
# Run at REPL: exec(open("/tests/test_wifi_capabilities.py").read())
# Read-only diagnostics: does not connect, disconnect, or change configuration.
# NOTE: scanning can temporarily disrupt normal Wi-Fi traffic.
import wifi
import time

radio = wifi.radio

def show(name, getter):
    try:
        value = getter()
        print("  {}: {}".format(name, value))
    except Exception as exc:
        print("  {}: {}: {}".format(name, type(exc).__name__, exc))

def mac_string(raw):
    if raw is None:
        return "(none)"
    try:
        return ":".join("{:02X}".format(x) for x in raw)
    except Exception:
        return repr(raw)

print("\n=== CLONKER WIFI CAPABILITY TEST ===")
print("Read-only association properties:")
for name in (
    "connected", "enabled", "ipv4_address", "ipv4_gateway",
    "ipv4_subnet", "ipv4_dns", "hostname", "tx_power",
):
    if hasattr(type(radio), name):
        show(name, lambda n=name: getattr(radio, n))
    else:
        print("  {}: (not exposed)".format(name))

show("MAC", lambda: mac_string(radio.mac_address))
show("AP info", lambda: radio.ap_info)

print("\nNames exposed by wifi.radio (no getters invoked):")
print(", ".join(n for n in dir(radio) if not n.startswith("_")))

print("\nNearby access points (single bounded scan):")
print("WARNING: scan can briefly affect Wi-Fi communications.")
started = time.monotonic()
count = 0
scan_started = False
try:
    networks = radio.start_scanning_networks()
    scan_started = True
    for ap in networks:
        count += 1
        try:
            ssid = ap.ssid
        except Exception:
            ssid = "(unavailable)"
        try:
            bssid = mac_string(ap.bssid)
        except Exception:
            bssid = "(unavailable)"
        try:
            channel = ap.channel
        except Exception:
            channel = "?"
        try:
            rssi = ap.rssi
        except Exception:
            rssi = "?"
        print("  {:2d}. SSID={!r} BSSID={} CH={} RSSI={}".format(
            count, ssid, bssid, channel, rssi))
        if count >= 40:
            print("  (stopped listing after 40 networks)")
            break
except Exception as exc:
    print("  Scan error: {}: {}".format(type(exc).__name__, exc))
finally:
    if scan_started:
        try:
            radio.stop_scanning_networks()
        except Exception as exc:
            print("  Scan cleanup: {}: {}".format(type(exc).__name__, exc))
print("Scan duration: {:.1f}s; networks listed: {}".format(
    time.monotonic() - started, count))
print("Connected after scan:")
show("connected", lambda: radio.connected)
show("IPv4", lambda: radio.ipv4_address)
print("=== END WIFI CAPABILITY TEST ===\n")
