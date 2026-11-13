# THE CLONKER 10000 - standalone Wi-Fi sleep experiment
# Location: firmware/tests/test_wifi_sleep.py
# Target: Raspberry Pi Pico 2 W / CircuitPython 10.3.1
# REPL: exec(open('/tests/test_wifi_sleep.py').read())
# Does not import or modify the Clonker application.

import gc
import os
import time
import ipaddress
import wifi

PING_HOST = "192.168.50.1"
PING_TIMEOUT_SECONDS = 1.0
OFF_SECONDS = 10
CYCLE_COUNT = 100
BETWEEN_CYCLES_SECONDS = 2

SSID = os.getenv("CIRCUITPY_WIFI_SSID")
PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")

attempts = 0
successes = 0
association_failures = 0
ping_failures = 0

best_ms = None
worst_ms = 0
sum_ms = 0

gc.collect()
initial_memory = gc.mem_free()
minimum_memory = initial_memory
initial_power_management = wifi.radio.power_management


def millis_since(start_ns):
    return (time.monotonic_ns() - start_ns) / 1_000_000


def memory():
    global minimum_memory
    gc.collect()
    free = gc.mem_free()
    minimum_memory = min(minimum_memory, free)
    return free


def report():
    print("Radio enabled:", wifi.radio.enabled)
    print("Connected:", wifi.radio.connected)
    print("IP:", wifi.radio.ipv4_address)
    print("Power management:", wifi.radio.power_management)
    print("Free memory:", memory(), "bytes")


def verify():
    if not wifi.radio.connected or wifi.radio.ipv4_address is None:
        print("VERIFY FAIL: no Wi-Fi association / IP")
        return "association"

    print("Association and IP: OK", wifi.radio.ipv4_address)

    if PING_HOST is None:
        return "ok"

    try:
        target = ipaddress.ip_address(PING_HOST)
        latency = wifi.radio.ping(
            target, timeout=PING_TIMEOUT_SECONDS
        )

        if latency is None:
            print("PING FAIL: no reply")
            return "ping"

        print("PING OK: {:.1f} ms".format(latency * 1000))
        return "ok"

    except Exception as exc:
        print("PING ERROR:", repr(exc))
        return "ping"


def radio_off():
    print("Disabling radio...")
    print("Power management before OFF:",
          wifi.radio.power_management)

    wifi.radio.enabled = False
    report()


def radio_on():
    global attempts, successes
    global association_failures, ping_failures
    global best_ms, worst_ms, sum_ms

    attempts += 1
    started = time.monotonic_ns()

    print("Enabling radio and reconnecting...")
    print("Power management before ON:",
          wifi.radio.power_management)

    try:
        wifi.radio.enabled = True

        print("Power management after enable:",
              wifi.radio.power_management)

        if not wifi.radio.connected:
            if not SSID:
                raise RuntimeError(
                    "No CIRCUITPY_WIFI_SSID in settings.toml"
                )
            wifi.radio.connect(SSID, PASSWORD)

        elapsed = millis_since(started)

        print("CONNECTED in {:.0f} ms".format(elapsed))
        print("Power management after connect:",
              wifi.radio.power_management)

        result = verify()

        if result == "ok":
            successes += 1
            sum_ms += elapsed
            best_ms = (
                elapsed if best_ms is None
                else min(best_ms, elapsed)
            )
            worst_ms = max(worst_ms, elapsed)
            memory()
            return True

        if result == "ping":
            ping_failures += 1
            print("Wi-Fi connected, but ping verification failed")
        else:
            association_failures += 1

    except Exception as exc:
        association_failures += 1
        print("RECONNECT ERROR after {:.0f} ms: {}".format(
            millis_since(started), repr(exc)
        ))

    memory()
    return False


def statistics():
    print("\n--- Statistics ---")
    print("Attempts:", attempts)
    print("Successes:", successes)
    print("Association/reconnect failures:",
          association_failures)
    print("Ping failures:", ping_failures)

    if successes:
        print(
            "Reconnect ms: min {:.0f}, avg {:.0f}, max {:.0f}".format(
                best_ms, sum_ms / successes, worst_ms
            )
        )

    print("Initial power management:",
          initial_power_management)
    print("Current power management:",
          wifi.radio.power_management)

    print("Initial free memory:", initial_memory)
    print("Minimum observed free memory:", minimum_memory)
    print("Current free memory:", memory())
    report()


def cycles(count=CYCLE_COUNT, off_seconds=OFF_SECONDS):
    print("\nRunning {} cycles; radio off {} seconds each".format(
        count, off_seconds
    ))
    print("Ctrl-C interrupts; no automatic reboot.")

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
    print("4  Single sleep/wake ({} seconds off)".format(
        OFF_SECONDS
    ))
    print("5  Automated {} cycles".format(CYCLE_COUNT))
    print("6  Statistics")
    print("q  Quit")


print("Wi-Fi sleep test - Pico 2 W / CircuitPython")
print("Ping target:", PING_HOST)
print("Credentials configured:", bool(SSID))
print("Initial power management:", initial_power_management)
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
