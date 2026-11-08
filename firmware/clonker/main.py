# The Clonker 10000
# clonker/main.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Application entry point and cooperative scheduler.

CONFIG mode runs the HTTP management interface; RUN mode stops it.
The shared action queue runs in either mode.

Fundamental and custom actions execute through the shared Dumb Queue.
Power and mute toggles use independent, volatile ON/OFF command histories.
Outbound HTTP requests are synchronous and blocking.
"""

import time
import gc

from clonker.system import logger
from clonker.system import perf
from clonker.net import web
from clonker import actions
from clonker import device_adapters
from clonker.controls import switches
from clonker.controls import physical
from clonker.display import oled
from clonker import device_config_v2 as device_config


# Physical GPIO controls are optional during development.
# False = brain-only mode; browser controls and action queue still work.
PHYSICAL_CONTROLS_ENABLED = True

# Cooperative scheduler intervals (integer nanoseconds).
# 1_000_000 ns = 1 ms; 1_000_000_000 ns = 1 second.
NS_PER_MS = 1_000_000

PHYSICAL_POLL_INTERVAL_NS = 1_000_000    # 1 ms
WEB_POLL_INTERVAL_NS = 1_000_000         # 1 ms
ACTION_POLL_INTERVAL_NS = 10_000_000     # 10 ms

# Lightweight serial performance diagnostics.
PERF_ENABLED = True
PERF_INTERVAL_NS = 30_000_000_000        # 30 seconds
SLOW_PHYSICAL_GAP_NS = 20_000_000        # 20 ms

# Scheduler branch attribution.
# A slow branch is one execution exceeding 20 ms.
PERF_BRANCH_PHYSICAL = 0
PERF_BRANCH_QUEUE = 1
PERF_BRANCH_ADAPTER = 2
PERF_BRANCH_WEB = 3
PERF_BRANCH_OLED = 4

PERF_BRANCH_NAMES = (
    "physical",
    "queue",
    "adapter",
    "web",
    "OLED",
)


def main():
    logger.info("THE CLONKER 10000")
    logger.info("Application started")

    # Load the active JSON configuration once at startup.
    settings = device_config.load()

    configured_rooms = settings["rooms"]

    logger.info(
        "{} room(s) loaded from JSON v{}".format(
            len(configured_rooms),
            device_config.CONFIG_VERSION
        )
    )

    # Log only rooms present in the active configuration.
    for room_id in device_config.ROOM_IDS:
        if room_id not in configured_rooms:
            continue

        room = configured_rooms[room_id]

        logger.info("{}: {}".format(room_id, room["name"]))

        for device_id in device_config.DEVICE_IDS:
            logger.info("  {} IP: {}".format(
                device_id.upper(), room["devices"][device_id]
            ))

        logger.info("  Fundamental actions: {}".format(
            len(room["actions"])
        ))

    # Initialize physical GPIO controls once at startup.
    physical_ready = False
    if PHYSICAL_CONTROLS_ENABLED:
        try:
            physical_ready = physical.initialize()
        except Exception as exc:
            logger.warning(
                "Physical controls initialization failed: {}".format(exc)
            )

    if not PHYSICAL_CONTROLS_ENABLED:
        logger.info("Physical controls disabled (brain-only mode)")

    web_running = False

    # Track announced mode and source independently.
    # None ensures both are announced on startup.
    last_announced_mode = None
    last_announced_source = None

    now = time.monotonic_ns()
    next_web_poll = now
    next_action_poll = now
    next_physical_poll = now

    # Performance statistics for periodic serial reporting.
    perf_report_at = now
    perf_last_physical = None
    perf_last_queue = None

    perf_physical_max = 0
    perf_physical_exec_max = 0
    perf_physical_gap_sum = 0
    perf_physical_gap_count = 0
    perf_physical_slow = 0

    perf_queue_max = 0
    perf_adapter_max = 0
    perf_oled_max = 0
    perf_loop_max = 0

    perf_web_max = 0
    perf_web_total = 0
    perf_web_count = 0

    # Fixed-size branch statistics.
    # Count executions exceeding the slow threshold and track
    # the maximum duration of those executions.
    perf_branch_counts = [0] * len(PERF_BRANCH_NAMES)
    perf_branch_max = [0] * len(PERF_BRANCH_NAMES)

    perf_oled_refresh_start = oled.get_refresh_count()

    # OLED is optional; failure must not stop Clonker.
    oled_ready = False
    if PHYSICAL_CONTROLS_ENABLED:
        try:
            oled_ready = oled.initialize()
            if oled_ready:
                logger.info("OLED initialized")
        except Exception as exc:
            logger.warning(
                "OLED unavailable: {}".format(exc)
            )

    try:
        while True:

            # Priority 1: Physical GPIO inputs.
            # Priority 2: Execute one eligible queued action.
            # Priority 3: Maintain stateful device adapters.
            # Priority 4: CONFIG management HTTP.
            #
            # The queue is polled in both CONFIG and RUN modes.
            now = time.monotonic_ns()
            if PERF_ENABLED:
                perf_loop_start = now

            if physical_ready and now >= next_physical_poll:
                if PERF_ENABLED:
                    if perf_last_physical is not None:
                        gap = now - perf_last_physical
                        perf_physical_gap_sum += gap
                        perf_physical_gap_count += 1

                        if gap > perf_physical_max:
                            perf_physical_max = gap

                        if gap > SLOW_PHYSICAL_GAP_NS:
                            perf_physical_slow += 1

                    perf_last_physical = now
                    perf_physical_start = time.monotonic_ns()

                physical.poll()

                if PERF_ENABLED:
                    elapsed = time.monotonic_ns() - perf_physical_start

                    if elapsed > perf_physical_exec_max:
                        perf_physical_exec_max = elapsed

                    if elapsed > SLOW_PHYSICAL_GAP_NS:
                        index = PERF_BRANCH_PHYSICAL
                        perf_branch_counts[index] += 1
                        if elapsed > perf_branch_max[index]:
                            perf_branch_max[index] = elapsed

                next_physical_poll = (
                    time.monotonic_ns() + PHYSICAL_POLL_INTERVAL_NS
                )

            if now >= next_action_poll:
                if PERF_ENABLED:
                    if perf_last_queue is not None:
                        gap = now - perf_last_queue
                        if gap > perf_queue_max:
                            perf_queue_max = gap
                    perf_last_queue = now
                    perf_action_start = time.monotonic_ns()

                actions.poll()

                if PERF_ENABLED:
                    elapsed = time.monotonic_ns() - perf_action_start

                    if elapsed > SLOW_PHYSICAL_GAP_NS:
                        index = PERF_BRANCH_QUEUE
                        perf_branch_counts[index] += 1
                        if elapsed > perf_branch_max[index]:
                            perf_branch_max[index] = elapsed

                next_action_poll = (
                    time.monotonic_ns() + ACTION_POLL_INTERVAL_NS
                )

            # Maintain stateful adapters independently of queue depth.
            if PERF_ENABLED:
                perf_adapter_start = time.monotonic_ns()

            try:
                device_adapters.poll()
            except Exception as exc:
                logger.warning(
                    "Device adapter maintenance failed: {}".format(exc)
                )

            if PERF_ENABLED:
                elapsed = time.monotonic_ns() - perf_adapter_start

                if elapsed > perf_adapter_max:
                    perf_adapter_max = elapsed

                if elapsed > SLOW_PHYSICAL_GAP_NS:
                    index = PERF_BRANCH_ADAPTER
                    perf_branch_counts[index] += 1
                    if elapsed > perf_branch_max[index]:
                        perf_branch_max[index] = elapsed

            # CONFIG/RUN is an application mode, not an HTTP command.
            config_mode = switches.config_enabled()
            config_source = switches.config_source()

            # Start/stop the management listener only when needed.
            if config_mode and not web_running:
                web.start()
                web_running = True

            elif not config_mode and web_running:
                web.stop()
                web_running = False

            # Announce the application mode source and state on startup
            # and whenever either changes. Never log every poll.
            if config_source != last_announced_source:
                logger.info("App mode source = {}".format(config_source))
                last_announced_source = config_source

            if config_mode != last_announced_mode:
                logger.info(
                    "App mode = {}".format(
                        "CONFIG" if config_mode else "RUN"
                    )
                )
                last_announced_mode = config_mode

            # Advance at most one inbound network operation per poll.
            if web_running:
                now = time.monotonic_ns()
                if now >= next_web_poll:
                    if PERF_ENABLED:
                        perf_web_start = time.monotonic_ns()

                    web.poll()

                    if PERF_ENABLED:
                        elapsed = time.monotonic_ns() - perf_web_start
                        perf_web_total += elapsed
                        perf_web_count += 1

                        if elapsed > perf_web_max:
                            perf_web_max = elapsed

                        if elapsed > SLOW_PHYSICAL_GAP_NS:
                            index = PERF_BRANCH_WEB
                            perf_branch_counts[index] += 1
                            if elapsed > perf_branch_max[index]:
                                perf_branch_max[index] = elapsed

                    next_web_poll = (
                        time.monotonic_ns() + WEB_POLL_INTERVAL_NS
                    )

            # Service the OLED after higher-priority work.
            if oled_ready:
                if PERF_ENABLED:
                    perf_oled_start = time.monotonic_ns()

                try:
                    oled.poll()
                except Exception as exc:
                    logger.warning(
                        "OLED poll failed: {}".format(exc)
                    )
                    oled.close()
                    oled_ready = False

                if PERF_ENABLED:
                    elapsed = time.monotonic_ns() - perf_oled_start

                    if elapsed > perf_oled_max:
                        perf_oled_max = elapsed

                    if elapsed > SLOW_PHYSICAL_GAP_NS:
                        index = PERF_BRANCH_OLED
                        perf_branch_counts[index] += 1
                        if elapsed > perf_branch_max[index]:
                            perf_branch_max[index] = elapsed

            # Performance summary: one report per interval.
            if PERF_ENABLED:
                perf_elapsed = time.monotonic_ns() - perf_loop_start

                if perf_elapsed > perf_loop_max:
                    perf_loop_max = perf_elapsed

                if (
                    time.monotonic_ns() - perf_report_at
                    >= PERF_INTERVAL_NS
                ):
                    average_gap_ms = (
                        perf_physical_gap_sum
                        / perf_physical_gap_count
                        / NS_PER_MS
                        if perf_physical_gap_count else 0.0
                    )

                    logger.info(
                        "PERF: physical gap avg={:.2f}ms, "
                        "max={:.2f}ms, >20ms={}".format(
                            average_gap_ms,
                            perf_physical_max / NS_PER_MS,
                            perf_physical_slow
                        )
                    )
                    logger.info(
                        "PERF: physical execution max={:.2f}ms".format(
                            perf_physical_exec_max / NS_PER_MS
                        )
                    )
                    logger.info(
                        "PERF: queue gap max={:.2f}ms".format(
                            perf_queue_max / NS_PER_MS
                        )
                    )
                    logger.info(
                        "PERF: adapter execution max={:.2f}ms".format(
                            perf_adapter_max / NS_PER_MS
                        )
                    )
                    logger.info(
                        "PERF: OLED execution max={:.2f}ms, "
                        "refreshes={}".format(
                            perf_oled_max / NS_PER_MS,
                            oled.get_refresh_count()
                            - perf_oled_refresh_start
                        )
                    )
                    logger.info(
                        "PERF: main loop max={:.2f}ms".format(
                            perf_loop_max / NS_PER_MS
                        )
                    )
                    logger.info(
                        "PERF: free memory={} bytes".format(
                            gc.mem_free()
                        )
                    )

                    average_web_ms = (
                        perf_web_total
                        / perf_web_count
                        / NS_PER_MS
                        if perf_web_count else 0.0
                    )
                    logger.info(
                        "PERF: mode={}, HTTP polls={}, "
                        "avg={:.2f}ms, max={:.2f}ms".format(
                            "CONFIG" if config_mode else "RUN",
                            perf_web_count,
                            average_web_ms,
                            perf_web_max / NS_PER_MS
                        )
                    )

                    # Report slow execution attribution.
                    worst_branch = -1
                    worst_duration = 0

                    for i in range(len(PERF_BRANCH_NAMES)):
                        count = perf_branch_counts[i]
                        duration = perf_branch_max[i]

                        if count:
                            logger.info(
                                "PERF: slow {} count={}, max={:.2f}ms".format(
                                    PERF_BRANCH_NAMES[i],
                                    count,
                                    duration / NS_PER_MS
                                )
                            )

                        if duration > worst_duration:
                            worst_duration = duration
                            worst_branch = i

                    if worst_branch >= 0:
                        logger.info(
                            "PERF: worst branch={} ({:.2f}ms)".format(
                                PERF_BRANCH_NAMES[worst_branch],
                                worst_duration / NS_PER_MS
                            )
                        )
                    else:
                        logger.info("PERF: no slow branches")

                    # Targeted physical dispatch measurements.
                    for name in (
                        "physical.dispatch",
                        "physical.hold",
                    ):
                        stat = perf.snapshot(name)

                        if stat is not None and stat["count"]:
                            logger.info(
                                "PERF: {} n={}, avg={:.2f}ms, "
                                "max={:.2f}ms, >20ms={}".format(
                                    name,
                                    stat["count"],
                                    stat["avg_ms"],
                                    stat["max_ms"],
                                    stat["slow_count"],
                                )
                            )

                    # Reset statistics for the next reporting window.
                    perf_physical_max = 0
                    perf_physical_exec_max = 0
                    perf_queue_max = 0
                    perf_adapter_max = 0
                    perf_oled_max = 0
                    perf_loop_max = 0
                    perf_web_max = 0
                    perf_web_total = 0
                    perf_web_count = 0
                    perf_physical_slow = 0
                    perf_physical_gap_sum = 0
                    perf_physical_gap_count = 0

                    for i in range(len(PERF_BRANCH_NAMES)):
                        perf_branch_counts[i] = 0
                        perf_branch_max[i] = 0

                    perf_oled_refresh_start = oled.get_refresh_count()
                    perf_report_at = time.monotonic_ns()

                    # Reset targeted measurements after reporting.
                    perf.reset("physical.dispatch")
                    perf.reset("physical.hold")

            # Yield briefly to the CircuitPython runtime.
            # Keep this INSIDE the while True loop.
            time.sleep(0.001)

    finally:
        if web_running:
            web.stop()
        device_adapters.close()
        if oled_ready:
            oled.close()
