# The Clonker 10000
# firmware/tests/test_flight_recorder.py
#
# Kitchen Sink regression tests for the flight recorder.
# Run from the CircuitPython REPL.
#
# Clonker Designed by David Jacobson

import gc

from clonker.system import flight_recorder as fr


def check(name, condition):
    """Report one assertion and fail immediately if false."""
    if not condition:
        print("FAIL:", name)
        raise AssertionError(name)
    print("PASS:", name)


def run():
    print()
    print("=== CLONKER FLIGHT RECORDER TEST ===")

    fr.clear()
    gc.collect()
    baseline = gc.mem_free()

    check("Initial count", fr.stats()["retained"] == 0)
    check("Initial total", fr.stats()["total"] == 0)
    check("Initial entries", fr.entries() == [])

    # Basic insertion and chronological ordering.
    for index in range(5):
        fr.record("EVENT {:03d}".format(index))

    check("Five entries retained", fr.stats()["retained"] == 5)
    check("Five total events", fr.stats()["total"] == 5)
    check("First entry", fr.entries()[0] == "EVENT 000")
    check("Last entry", fr.entries()[-1] == "EVENT 004")

    # Fill beyond capacity to force circular overwrite.
    fr.clear()

    total = fr.CAPACITY + 20

    for index in range(total):
        fr.record("EVENT {:03d}".format(index))

    stats = fr.stats()
    history = fr.entries()

    check("Capacity enforced", stats["retained"] == fr.CAPACITY)
    check("Total recorded", stats["total"] == total)
    check("Overwrite count", stats["overwritten"] == 20)
    check("Oldest retained",
          history[0] == "EVENT 020")
    check("Newest retained",
          history[-1] == "EVENT {:03d}".format(total - 1))

    check(
        "Chronological order",
        all(
            history[index] == "EVENT {:03d}".format(index + 20)
            for index in range(fr.CAPACITY)
        )
    )

    # Drop the temporary history copy before measuring RAM.
    history = None
    gc.collect()

    populated_free = gc.mem_free()
    retained_bytes = baseline - populated_free

    print()
    print("RAM baseline free:  {} bytes".format(baseline))
    print("RAM populated free: {} bytes".format(populated_free))
    print("RAM difference:     {} bytes".format(retained_bytes))

    # Clear and confirm reset behavior.
    fr.clear()
    gc.collect()

    check("Clear empties entries", fr.entries() == [])
    check("Clear resets count", fr.stats()["retained"] == 0)
    check("Clear resets total", fr.stats()["total"] == 0)
    check("Clear resets overwrites",
          fr.stats()["overwritten"] == 0)

    print("RAM after clear:   {} bytes".format(gc.mem_free()))
    print()
    print("=== ALL FLIGHT RECORDER TESTS PASSED ===")


if __name__ == "__main__":
    run()
