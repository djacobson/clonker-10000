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
from clonker.system import memory_monitor
from clonker.net import web
from clonker.net import http_transport
from clonker.devices import denon
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
PHYSICAL_POLL_INTERVAL_NS = 1_000_000
WEB_POLL_INTERVAL_NS = 1_000_000
ACTION_POLL_INTERVAL_NS = 10_000_000
WEB_LISTENER_RETRY_NS = 5_000_000_000  # 5 seconds

# Periodic performance reporting.
PERF_ENABLED = False
PERF_INTERVAL_NS = 30_000_000_000

# Share the scheduler's PERF switch with outbound HTTP.
http_transport.HTTP_PERF_ENABLED = PERF_ENABLED
denon.DENON_PERF_ENABLED = PERF_ENABLED
memory_monitor.GC_PERF_ENABLED = PERF_ENABLED

# Scheduler measurements, in reporting order.
PERF_SCHEDULER = (
    "physical.exec",
    "queue.exec",
    "adapter.exec",
    "web.exec",
    "oled.exec",
)

# Targeted physical measurements.
PERF_PHYSICAL = (
    "physical.scan",
    "physical.events",
    "physical.events.active",
    "physical.events.idle",
    "physical.non_scan",
    "physical.slow.scan",
    "physical.slow.non_scan",
    "physical.volume",
    "physical.dispatch",
    "physical.hold",
)

# Outbound HTTP transport measurements, in reporting order.
PERF_HTTP = (
    "http.connect",
    "http.send",
    "http.response",
    "http.total",
    "http.failure.total",
    "http.failure.socket",
    "http.failure.connect",
    "http.failure.send",
    "http.failure.response",
)

# Persistent Denon TCP measurements, in reporting order.
PERF_DENON = (
    "denon.connect",
    "denon.send",
    "denon.total",
    "denon.failure.connect",
    "denon.failure.send",
    "denon.failure.total",
)

# Register all scheduler measurements once.
# Physical control measurements are registered by physical.py.
for _name in (
    "physical.gap",
    "loop.exec",
) + PERF_SCHEDULER:
    perf.register(_name)


def _report_stat(name, label=None, slow_only=False):
    """Report one registered performance measurement.

    Returns its maximum duration in milliseconds.
    """
    stat = perf.snapshot(name)

    if stat is None or not stat["count"]:
        return 0.0

    if slow_only and not stat["slow_count"]:
        return stat["max_ms"]

    logger.info(
        "PERF: {} n={}, avg={:.2f}ms, "
        "max={:.2f}ms, >20ms={}".format(
            label or name,
            stat["count"],
            stat["avg_ms"],
            stat["max_ms"],
            stat["slow_count"],
        )
    )

    return stat["max_ms"]


def _report_performance(config_mode, oled_refresh_start):
    """Emit one concise performance report.

    All measurements share the same reporting interval.
    """
    logger.info(
        "PERF: mode={}".format(
            "CONFIG" if config_mode else "RUN"
        )
    )

    # Responsiveness: time between physical polls.
    _report_stat("physical.gap", "GPIO gap")

    # Physical polling and its constituent operations.
    _report_stat("physical.exec", "physical execution")

    for name in PERF_PHYSICAL:
        _report_stat(name)

    # Previous reporting boundary's explicit GC duration.
    _report_stat("gc.collect", "GC collection")

    # Scheduler operations: report only slow branches.
    worst_name = None
    worst_ms = 0.0

    for name in PERF_SCHEDULER:
        stat = perf.snapshot(name)

        if stat is None or not stat["slow_count"]:
            continue

        _report_stat(name, "slow " + name)

        if stat["max_ms"] > worst_ms:
            worst_ms = stat["max_ms"]
            worst_name = name

    if worst_name is not None:
        logger.info(
            "PERF: worst branch={} ({:.2f}ms)".format(
                worst_name, worst_ms
            )
        )
    else:
        logger.info("PERF: no slow branches")

    # Outbound HTTP timing, separate from management web polling.
    http_total = perf.snapshot("http.total")
    http_failed = perf.snapshot("http.failure.total")

    if (
        (http_total is not None and http_total["count"])
        or (http_failed is not None and http_failed["count"])
    ):
        logger.info("PERF: outbound HTTP")

        for name in PERF_HTTP:
            _report_stat(name)

    # Persistent Denon TCP timing, separate from outbound HTTP.
    denon_total = perf.snapshot("denon.total")
    denon_failed = perf.snapshot("denon.failure.total")

    if (
        (denon_total is not None and denon_total["count"])
        or (denon_failed is not None and denon_failed["count"])
    ):
        logger.info("PERF: Denon TCP")

        for name in PERF_DENON:
            _report_stat(name)

    # Preserve useful context without duplicating timing data.
    _report_stat("loop.exec", "main loop")

    web_stat = perf.snapshot("web.exec")
    if web_stat is not None:
        logger.info(
            "PERF: management HTTP polls={}".format(
                web_stat["count"]
            )
        )

    logger.info(
        "PERF: OLED refreshes={}".format(
            oled.get_refresh_count() - oled_refresh_start
        )
    )

    logger.info(
        "PERF: free memory={} bytes".format(
            memory_monitor.free_bytes()
        )
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
            logger.info(
                "  {} IP: {}".format(
                    device_id.upper(),
                    room["devices"][device_id]
                )
            )

        logger.info(
            "  Fundamental actions: {}".format(
                len(room["actions"])
            )
        )

    # Initialize physical GPIO controls once at startup.
    physical_ready = False

    if PHYSICAL_CONTROLS_ENABLED:
        try:
            physical_ready = physical.initialize()
        except Exception as exc:
            logger.warning(
                "Physical controls initialization failed: {}".format(
                    exc
                )
            )

    if not PHYSICAL_CONTROLS_ENABLED:
        logger.info(
            "Physical controls disabled (brain-only mode)"
        )

    web_running = False

    # Track announced mode and source independently.
    last_announced_mode = None
    last_announced_source = None

    now = time.monotonic_ns()
    next_web_poll = now
    next_web_retry = now
    next_action_poll = now
    next_physical_poll = now

    perf_report_at = now
    perf_last_physical = None
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

    # Announce successful application initialization.
    # The normal OLED idle timeout clears this automatically.
    if oled_ready:
        oled.show_text("CLONKER", "READY!")

    # Initialize memory monitoring after startup configuration.
    memory_monitor.initialize()

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
                        perf.record(
                            "physical.gap",
                            now - perf_last_physical
                        )

                    perf_last_physical = now
                    started = perf.start()

                try:
                    physical.poll()
                finally:
                    if PERF_ENABLED:
                        perf.stop("physical.exec", started)

                next_physical_poll = (
                    time.monotonic_ns()
                    + PHYSICAL_POLL_INTERVAL_NS
                )

            if now >= next_action_poll:
                if PERF_ENABLED:
                    started = perf.start()

                try:
                    actions.poll()
                finally:
                    if PERF_ENABLED:
                        perf.stop("queue.exec", started)

                next_action_poll = (
                    time.monotonic_ns()
                    + ACTION_POLL_INTERVAL_NS
                )

            # Maintain stateful adapters independently of queue depth.
            if PERF_ENABLED:
                started = perf.start()

            try:
                device_adapters.poll()
            except Exception as exc:
                logger.warning(
                    "Device adapter maintenance failed: {}".format(
                        exc
                    )
                )
            finally:
                if PERF_ENABLED:
                    perf.stop("adapter.exec", started)

            # CONFIG/RUN is an application mode, not an HTTP command.
            config_mode = switches.config_enabled()
            config_source = switches.config_source()

            # Start/retry the CONFIG listener with bounded backoff.
            if config_mode and not web_running:
                if now >= next_web_retry:
                    try:
                        web.start()
                    except (OSError, RuntimeError) as error:
                        logger.warning(
                            "HTTP listener start failed: {}".format(error)
                        )
                        next_web_retry = (
                            time.monotonic_ns()
                            + WEB_LISTENER_RETRY_NS
                        )
                    else:
                        web_running = True

            elif not config_mode and web_running:
                web_running = False
                try:
                    web.stop()
                except OSError as error:
                    logger.warning(
                        "HTTP listener stop failed: {}".format(error)
                    )

            if not config_mode:
                # Next CONFIG entry can attempt startup immediately.
                next_web_retry = now

            # Announce the application mode source and state on startup
            # and whenever either changes. Never log every poll.
            if config_source != last_announced_source:
                logger.info(
                    "App mode source = {}".format(config_source)
                )
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
                        started = perf.start()

                    try:
                        web.poll()

                    except MemoryError:
                        # HTTP memory exhaustion must not terminate
                        # the physical remote application.
                        web.abort_low_memory()
                        gc.collect()
                        logger.warning(
                            "HTTP memory allocation failed; "
                            "client discarded"
                        )

                    except OSError as error:
                        # Unexpected listener/accept failure.
                        # Tear down and retry after the configured delay.
                        logger.warning(
                            "HTTP network error; restarting listener: {}".format(
                                error
                            )
                        )
                        web_running = False
                        try:
                            web.stop()
                        except OSError as close_error:
                            logger.warning(
                                "HTTP listener cleanup failed: {}".format(
                                    close_error
                                )
                            )
                        next_web_retry = (
                            time.monotonic_ns()
                            + WEB_LISTENER_RETRY_NS
                        )

                    finally:
                        if PERF_ENABLED:
                            perf.stop("web.exec", started)

                    next_web_poll = (
                        time.monotonic_ns()
                        + WEB_POLL_INTERVAL_NS
                    )

            # Service the OLED after higher-priority work.
            if oled_ready:
                if PERF_ENABLED:
                    started = perf.start()

                try:
                    oled.poll()
                except Exception as exc:
                    logger.warning(
                        "OLED poll failed: {}".format(exc)
                    )
                    oled.close()
                    oled_ready = False
                finally:
                    if PERF_ENABLED:
                        perf.stop("oled.exec", started)

            # Performance summary: one report per interval.
            if PERF_ENABLED:
                perf.stop("loop.exec", perf_loop_start)

                if (
                    time.monotonic_ns() - perf_report_at
                    >= PERF_INTERVAL_NS
                ):
                    _report_performance(
                        config_mode,
                        perf_oled_refresh_start
                    )

                    # Reset all registered timing measurements.
                    perf.reset()
                    perf_oled_refresh_start = (
                        oled.get_refresh_count()
                    )
                    perf_report_at = time.monotonic_ns()

            # Scheduled memory diagnostics and optional GC experiment.
            memory_monitor.poll()

            # Yield briefly to the CircuitPython runtime.
            # Keep this INSIDE the while True loop.
            time.sleep(0.001)

    finally:
        if web_running:
            web.stop()

        device_adapters.close()

        if oled_ready:
            oled.close()
