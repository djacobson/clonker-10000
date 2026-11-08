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

from clonker.system import logger
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

# Cooperative scheduler intervals.
PHYSICAL_POLL_INTERVAL = 0.001
WEB_POLL_INTERVAL = 0.001
ACTION_POLL_INTERVAL = 0.01

# Lightweight serial performance diagnostics.
PERF_ENABLED = True
PERF_INTERVAL = 30.0

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
            logger.warning("Physical controls initialization failed: {}".format(exc))

    if not PHYSICAL_CONTROLS_ENABLED:
        logger.info("Physical controls disabled (brain-only mode)")

    web_running = False

    # Track announced mode and source independently.
    # None ensures both are announced on startup.
    last_announced_mode = None
    last_announced_source = None

    next_web_poll = time.monotonic()
    next_action_poll = time.monotonic()
    next_physical_poll = time.monotonic()

    # Performance statistics for periodic serial reporting.
    perf_report_at = time.monotonic()
    perf_last_physical = None
    perf_last_queue = None

    perf_physical_max = 0.0
    perf_queue_max = 0.0
    perf_oled_max = 0.0
    perf_loop_max = 0.0
    perf_physical_slow = 0
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
            now = time.monotonic()
            if PERF_ENABLED:
                perf_loop_start = now

            if physical_ready and now >= next_physical_poll:
                if PERF_ENABLED:
                    if perf_last_physical is not None:
                        gap = now - perf_last_physical
                        if gap > perf_physical_max:
                            perf_physical_max = gap
                        if gap > 0.020:
                            perf_physical_slow += 1
                    perf_last_physical = now

                physical.poll()
                next_physical_poll = (
                    time.monotonic() + PHYSICAL_POLL_INTERVAL
                )

            if now >= next_action_poll:
                if PERF_ENABLED:
                    if perf_last_queue is not None:
                        gap = now - perf_last_queue
                        if gap > perf_queue_max:
                            perf_queue_max = gap
                    perf_last_queue = now

                actions.poll()
                next_action_poll = time.monotonic() + ACTION_POLL_INTERVAL

            # Maintain stateful adapters independently of queue depth.
            try:
                device_adapters.poll()
            except Exception as exc:
                logger.warning(
                    "Device adapter maintenance failed: {}".format(exc)
                )

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
                now = time.monotonic()
                if now >= next_web_poll:
                    web.poll()
                    next_web_poll = (
                        time.monotonic() + WEB_POLL_INTERVAL
                    )

            # Service the OLED after higher-priority work.
            if oled_ready:
                if PERF_ENABLED:
                    perf_oled_start = time.monotonic()

                try:
                    oled.poll()
                except Exception as exc:
                    logger.warning(
                        "OLED poll failed: {}".format(exc)
                    )
                    oled.close()
                    oled_ready = False

                if PERF_ENABLED:
                    elapsed = time.monotonic() - perf_oled_start
                    if elapsed > perf_oled_max:
                        perf_oled_max = elapsed

            # Performance summary: one report per interval.
            if PERF_ENABLED:
                perf_elapsed = time.monotonic() - perf_loop_start

                if perf_elapsed > perf_loop_max:
                    perf_loop_max = perf_elapsed

                if time.monotonic() - perf_report_at >= PERF_INTERVAL:
                    logger.info(
                        "PERF: physical max gap={:.1f}ms, >20ms={}".format(
                            perf_physical_max * 1000,
                            perf_physical_slow
                        )
                    )
                    logger.info(
                        "PERF: queue max gap={:.1f}ms".format(
                            perf_queue_max * 1000
                        )
                    )
                    logger.info(
                        "PERF: OLED max poll={:.1f}ms, refreshes={}".format(
                            perf_oled_max * 1000,
                            oled.get_refresh_count() - perf_oled_refresh_start
                        )
                    )
                    logger.info(
                        "PERF: main loop max={:.1f}ms".format(
                            perf_loop_max * 1000
                        )
                    )

                    perf_physical_max = 0.0
                    perf_queue_max = 0.0
                    perf_oled_max = 0.0
                    perf_loop_max = 0.0
                    perf_physical_slow = 0
                    perf_oled_refresh_start = oled.get_refresh_count()
                    perf_report_at = time.monotonic()

            # Yield briefly to the CircuitPython runtime.
            # Keep this INSIDE the while True loop.
            time.sleep(0.001)

    finally:
        if web_running:
            web.stop()
        device_adapters.close()
        if oled_ready:
            oled.close()
