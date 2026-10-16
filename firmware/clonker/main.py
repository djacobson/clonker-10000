# The Clonker 10000
# clonker/main.py
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

import time

from clonker import logger
from clonker import web
from clonker.controls import switches
from clonker import device_config_v2 as device_config

# Management HTTP service is low priority.
WEB_POLL_INTERVAL = 0.01


def main():
    logger.info("THE CLONKER 10000")
    logger.info("Application started")

    settings = device_config.load()
    logger.info("Three-room configuration loaded from JSON v2")

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
            # Priority 1: GPIO inputs (future)
            # Priority 2: Event dispatcher (future)
            # Priority 3: Timers (future)
            # Priority 4: CONFIG web interface
            config_mode = switches.config_enabled()

            if config_mode and not web_running:
                web.start()
                web_running = True
                logger.info("CONFIG mode enabled")

            elif not config_mode and web_running:
                web.stop()
                web_running = False
                logger.info("RUN mode enabled")

            if web_running:
                now = time.monotonic()
                if now >= next_web_poll:
                    web.poll()
                    next_web_poll = time.monotonic() + WEB_POLL_INTERVAL
    finally:
        if web_running:
            web.stop()
