# The Clonker 10000
# clonker/system/memory_monitor.py
#
# Clonker Designed by David Jacobson

"""Scheduled memory diagnostics and optional GC experiment.

Memory monitoring and the legacy periodic GC experiment are
independently configurable.

No history is accumulated and no data is written to flash.
"""

import gc
import time

from clonker.system import logger
from clonker.system import perf


# Long-duration memory diagnostics.
MEMORY_MONITOR_ENABLED = True
MEMORY_MONITOR_INTERVAL_NS = 300_000_000_000  # 5 minutes

# Legacy TEST 7: explicit garbage collection every 2 seconds.
# Keep disabled during the overnight memory investigation.
GC_TEST_ENABLED = False
GC_INTERVAL_NS = 2_000_000_000
GC_PERF_ENABLED = False

perf.register("gc.collect")

_started_at = None
_next_memory_at = None
_next_gc_at = None
_baseline_free = None
_lowest_free = None


def _collect():
    """Collect garbage with optional PERF timing."""
    if GC_PERF_ENABLED:
        started = perf.start()
        gc.collect()
        perf.stop("gc.collect", started)
    else:
        gc.collect()


def _sample(initial=False):
    """Report retained heap usage after garbage collection."""
    global _baseline_free, _lowest_free

    _collect()

    free = gc.mem_free()
    allocated = gc.mem_alloc()

    if _baseline_free is None:
        _baseline_free = free
        _lowest_free = free

    if free < _lowest_free:
        _lowest_free = free

    elapsed_seconds = (
        (time.monotonic_ns() - _started_at) // 1_000_000_000
    )

    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60

    logger.info(
        "MEM: uptime={:02d}:{:02d}:{:02d}, "
        "free={}, allocated={}".format(
            hours, minutes, seconds, free, allocated
        )
    )

    logger.info(
        "MEM: baseline_free={}, change={}, lowest_free={}".format(
            _baseline_free,
            free - _baseline_free,
            _lowest_free,
        )
    )


def initialize():
    """Initialize independent monitoring schedules."""
    global _started_at, _next_memory_at, _next_gc_at
    global _baseline_free, _lowest_free

    now = time.monotonic_ns()

    _started_at = now
    _next_memory_at = now + MEMORY_MONITOR_INTERVAL_NS
    _next_gc_at = now + GC_INTERVAL_NS
    _baseline_free = None
    _lowest_free = None

    if MEMORY_MONITOR_ENABLED:
        _sample(initial=True)


def poll():
    """Run scheduled memory diagnostics without blocking for delays."""
    global _next_memory_at, _next_gc_at

    if _started_at is None:
        return

    now = time.monotonic_ns()

    if MEMORY_MONITOR_ENABLED and now >= _next_memory_at:
        _sample()
        _next_memory_at = (
            time.monotonic_ns() + MEMORY_MONITOR_INTERVAL_NS
        )

    # Independent legacy experiment, disabled by default.
    if GC_TEST_ENABLED and now >= _next_gc_at:
        _collect()
        _next_gc_at = time.monotonic_ns() + GC_INTERVAL_NS
