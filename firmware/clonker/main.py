# The Clonker 10000
# clonker/main.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Application entry point and cooperative scheduler.

CONFIG mode runs the HTTP management interface; RUN mode stops it.
Future physical controls, command dispatch, and timers take precedence
in the main loop. Keep web polling lightweight and nonblocking.
"""

import time

from clonker import logger
from clonker import web
from clonker.controls import switches
from clonker import device_config_v2 as device_config


# Management HTTP service is low priority. Poll at most once per interval.
WEB_POLL_INTERVAL = 0.01


def main():
    logger.info("THE CLONKER 10000")
    logger.info("Application started")

    # Load the production JSON v2 configuration once at startup.
    # The config engine binds subsequent saves to the successfully loaded path.
    settings = device_config.load()
    logger.info("Three-room configuration loaded from JSON v2")

    # Log the configured rooms and endpoint addresses for bench diagnostics.
    # Blank device IP addresses are valid: those endpoints are unconfigured.
    for room_id in device_config.ROOM_IDS:
        room = settings["rooms"][room_id]
        logger.info("{}: {}".format(room_id, room["name"]))

        for device_id in device_config.DEVICE_IDS:
            logger.info("  {} IP: {}".format(
                device_id.upper(), room["devices"][device_id]
            ))

        logger.info("  Fundamental actions: {}".format(
            len(room["actions"])
        ))

    web_running = False
    next_web_poll = time.monotonic()

    try:
        while True:
            # Planned scheduler priorities:
            # Priority 1: GPIO inputs (future)
            # Priority 2: Event dispatcher (future)
            # Priority 3: Timers (future)
            # Priority 4: CONFIG web interface
            #
            # CONFIG/RUN is a physical mode, not an HTTP command.
            config_mode = switches.config_enabled()

            # Start/stop the listener only on a mode transition.
            if config_mode and not web_running:
                web.start()
                web_running = True
                logger.info("CONFIG mode enabled")

            elif not config_mode and web_running:
                web.stop()
                web_running = False
                logger.info("RUN mode enabled")

            # poll() advances a single network operation; it must not
            # monopolize the loop once physical controls are implemented.
            if web_running:
                now = time.monotonic()
                if now >= next_web_poll:
                    web.poll()
                    next_web_poll = time.monotonic() + WEB_POLL_INTERVAL

    finally:
        # Always close the listener if the main loop exits unexpectedly.
        if web_running:
            web.stop()
