# THE CLONKER 10000 - standalone Wi-Fi sleep experiment
# Location in repository: firmware/tests/test_wifi_sleep.py
# Target: Raspberry Pi Pico 2 W / CircuitPython 10.3.1
# Run from REPL: exec(open('/tests/test_wifi_sleep.py').read())
# Does not import or modify the Clonker application.

import gc
import os
import time
import ipaddress
import wifi

# Adjust to a known local host that responds to ICMP.
# Set to None to skip ping checks.
PING_HOST = "192.168.50.1"
PING_TIMEOUT_SECONDS = 1.0
OFF_SECONDS = 10
CYCLE_COUNT = 100
BETWEEN_CYCLES_SECONDS = 2

# CircuitPython's normal Wi-Fi environment variable names.
SSID = os.getenv("CIRCUITPY_WIFI_SSID")
PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")

attempts = 0
successes = 0
failures = 0
best_ms = None
worst_ms = 0
sum_ms = 0


def millis_since(start_ns):
    return (time.monotonic_ns() - start_ns) / 1_000_000


def report():
    gc.collect()
    print("Radio enabled:", wifi.radio.enabled)
    print("Connected:", wifi.radio.connected)
    print("IP:", wifi.radio.ipv4_address)
    print("Free memory:", gc.mem_free(), "bytes")


def verify():
    if not wifi.radio.connected or wifi.radio.ipv4_address is None:
        print("VERIFY FAIL: no Wi-Fi association / IP")
        return False
    print("Association and IP: OK", wifi.radio.ipv4_address)
    if PING_HOST is None:
        return True
    try:
        target = ipaddress.ip_address(PING_HOST)
        latency = wifi.radio.ping(target, timeout=PING_TIMEOUT_SECONDS)
        if latency is None:
            print("PING: no reply (host may block ICMP)")
            return False
        print("PING OK: {:.1f} ms".format(latency * 1000))
        return True
    except Exception as exc:
        print("PING ERROR:", repr(exc))
        return False


def radio_off():
    print("Disabling radio...")
    wifi.radio.enabled = False
    print("Radio enabled:", wifi.radio.enabled)
    report()


def radio_on():
    global attempts, successes, failures, best_ms, worst_ms, sum_ms
    attempts += 1
    started = time.monotonic_ns()
    print("Enabling radio and reconnecting...")
    try:
        wifi.radio.enabled = True
        if not wifi.radio.connected:
            if not SSID:
                raise RuntimeError("No CIRCUITPY_WIFI_SSID in settings.toml")
            wifi.radio.connect(SSID, PASSWORD)
        elapsed = millis_since(started)
        # Time measures radio enable + association + IP acquisition.
        # Ping is separately measured and is not included in this time.
        print("CONNECTED in {:.0f} ms".format(elapsed))
        if verify():
            successes += 1
            sum_ms += elapsed
            best_ms = elapsed if best_ms is None else min(best_ms, elapsed)
            worst_ms = max(worst_ms, elapsed)
            return True
        failures += 1
        print("VERIFY FAILED: association may still be up")
    except Exception as exc:
        failures += 1
        print("RECONNECT ERROR after {:.0f} ms: {}".format(
            millis_since(started), repr(exc)))
    return False


def statistics():
    print("\n--- Statistics ---")
    print("Attempts:", attempts, "Success:", successes, "Failure:", failures)
    if successes:
        print("Reconnect ms: min {:.0f}, avg {:.0f}, max {:.0f}".format(
            best_ms, sum_ms / successes, worst_ms))
    report()


def cycles(count=CYCLE_COUNT, off_seconds=OFF_SECONDS):
    print("\nRunning {} cycles; radio off {} seconds each".format(
        count, off_seconds))
    print("Ctrl-C interrupts the test; no automatic reboot.")
    for i in range(count):
        print("\nCYCLE {}/{}".format(i + 1, count))
        radio_off()
        time.sleep(off_seconds)
        if not radio_on():
            print("STOPPING on failed reconnect/verification")
            break
        if i + 1 < count:
            time.sleep(BETWEEN_CYCLES_SECONDS)
    statistics()


def menu():
    print("\n--- Wi-Fi Sleep Kitchen Sink ---")
    print("1  Status / verify")
    print("2  Wi-Fi OFF (leave off for power measurement)")
    print("3  Wi-Fi ON / reconnect")
    print("4  Single sleep/wake ({} seconds off)".format(OFF_SECONDS))
    print("5  Automated {} cycles".format(CYCLE_COUNT))
    print("6  Statistics")
    print("q  Quit")


print("Wi-Fi sleep test - Pico 2 W / CircuitPython")
print("Ping target:", PING_HOST)
print("Credentials configured:", bool(SSID))
report()

try:
    while True:
        menu()
        choice = input("Choice: ").strip().lower()
        if choice == "1":
            report()
            if wifi.radio.enabled:
                verify()
        elif choice == "2":
            radio_off()
        elif choice == "3":
            radio_on()
        elif choice == "4":
            cycles(1, OFF_SECONDS)
        elif choice == "5":
            cycles()
        elif choice == "6":
            statistics()
        elif choice == "q":
            break
        else:
            print("Unknown choice")
except KeyboardInterrupt:
    print("\nInterrupted by operator")
finally:
    print("Exiting test; radio state unchanged.")
    statistics()
