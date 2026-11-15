# The Clonker 10000
# tests/test_denon_memory.py
#
# Chapter 10 -- Operation Catch the Gremlin
# Denon persistent TCP memory experiment
#
# Clonker Designed by David Jacobson

import gc
import time
import traceback
import wifi

from clonker import device_config_v2 as device_config
from clonker.devices import denon


ROOM_ID = "room-1"
DEVICE_ID = "device-2"

# Each cycle sends equal numbers of UP and DOWN commands.
# Keep these modest until the behavior is understood.
PAIRS_PER_CYCLE = 30
CYCLES = 3

# Time between accepted commands, in seconds.
COMMAND_INTERVAL = 0.10
POLL_INTERVAL = 0.005
SEND_TIMEOUT = 3.0

# Observe the connection while idle, before closing it.
IDLE_SECONDS = 20
SAMPLE_INTERVAL = 5


def sample(label):
    gc.collect()

    free = gc.mem_free()
    allocated = gc.mem_alloc()

    print(
        "MEM:",
        label,
        "free=", free,
        "allocated=", allocated,
        "total=", free + allocated
    )

    return free


def send_when_ready(endpoint, command):
    started = time.monotonic()

    while True:
        # Drain responses from previous commands before
        # attempting the next command.
        denon.poll_rx()

        if denon.send_volume(endpoint, command):
            return

        if time.monotonic() - started > SEND_TIMEOUT:
            raise RuntimeError("Denon pacing timeout")

        time.sleep(POLL_INTERVAL)


def idle_observation(seconds):
    started = time.monotonic()

    while time.monotonic() - started < seconds:
        time.sleep(SAMPLE_INTERVAL)
        sample("IDLE / SOCKET OPEN")


def run():
    print()
    print("THE CLONKER 10000")
    print("OPERATION CATCH THE GREMLIN")
    print("DENON MEMORY EXPERIMENT")
    print("--------------------------------")

    if not wifi.radio.connected:
        print("FAIL: Wi-Fi disconnected")
        return

    settings = device_config.load()
    room = settings["rooms"][ROOM_ID]
    endpoint = room["devices"][DEVICE_ID]

    if not endpoint:
        print("FAIL: Denon endpoint not configured")
        return

    print("Room:", room["name"])
    print("Endpoint:", endpoint)
    print("Pairs per cycle:", PAIRS_PER_CYCLE)
    print("Cycles:", CYCLES)
    print("Commands per cycle:", PAIRS_PER_CYCLE * 2)
    print()

    denon.close()
    baseline = sample("BASELINE")

    try:
        for cycle in range(1, CYCLES + 1):
            print()
            print("=== CYCLE", cycle, "===")

            print("PHASE 1: CONNECT")
            denon.connect(endpoint)
            sample("CONNECTED")

            print("PHASE 2: VOLUME COMMANDS")

            for index in range(PAIRS_PER_CYCLE):
                send_when_ready(endpoint, "MVUP")
                time.sleep(COMMAND_INTERVAL)

                send_when_ready(endpoint, "MVDOWN")
                time.sleep(COMMAND_INTERVAL)

                if (index + 1) % 10 == 0:
                    sample(
                        "ACTIVE PAIR {}".format(index + 1)
                    )

            sample("AFTER COMMANDS")

            print("PHASE 3: IDLE WITH SOCKET OPEN")
            idle_observation(IDLE_SECONDS)

            print("PHASE 4: CLOSE SOCKET")
            denon.close()
            sample("AFTER CLOSE")

            time.sleep(2)
            sample("AFTER CLOSE + 2 SEC")

        print()
        print("=== TEST COMPLETE ===")
        final = sample("FINAL")

        print("Baseline free:", baseline)
        print("Final free:", final)
        print("Difference:", final - baseline)

    except Exception as error:
        print()
        print("FAIL:", repr(error))
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    finally:
        denon.close()
        sample("FINAL CLEANUP")
        print("Denon connection closed")


run()
