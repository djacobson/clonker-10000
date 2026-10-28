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
from clonker.controls import switches
from clonker.controls import physical
from clonker import device_config_v2 as device_config


# Physical GPIO controls are optional during development.
# False = brain-only mode; browser controls and action queue still work.
PHYSICAL_CONTROLS_ENABLED = False

# Cooperative scheduler intervals.
PHYSICAL_POLL_INTERVAL = 0.01
WEB_POLL_INTERVAL = 0.01
ACTION_POLL_INTERVAL = 0.01


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
    next_web_poll = time.monotonic()
    next_action_poll = time.monotonic()
    next_physical_poll = time.monotonic()

    try:
        while True:

            # Priority 1: Physical GPIO inputs.
            # Priority 2: Execute one eligible queued action.
            # Priority 3: CONFIG management HTTP.
            #
            # The queue is polled in both CONFIG and RUN modes.
            now = time.monotonic()

            if physical_ready and now >= next_physical_poll:
                physical.poll()
                next_physical_poll = (
                    time.monotonic() + PHYSICAL_POLL_INTERVAL
                )

            if now >= next_action_poll:
                actions.poll()
                next_action_poll = time.monotonic() + ACTION_POLL_INTERVAL

            # CONFIG/RUN is an application mode, not an HTTP command.
            config_mode = switches.config_enabled()

            # Start/stop listener only on a mode transition.
            if config_mode and not web_running:
                web.start()
                web_running = True
                logger.info("CONFIG mode enabled")

            elif not config_mode and web_running:
                web.stop()
                web_running = False
                logger.info("RUN mode enabled")

            # Advance at most one inbound network operation per poll.
            if web_running:
                now = time.monotonic()
                if now >= next_web_poll:
                    web.poll()
                    next_web_poll = (
                        time.monotonic() + WEB_POLL_INTERVAL
                    )

            # Yield briefly to the CircuitPython runtime.
            # Keep this INSIDE the while True loop.
            time.sleep(0.001)

    finally:
        if web_running:
            web.stop()
