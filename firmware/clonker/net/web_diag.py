# The Clonker 10000
# clonker/net/web_diag.py -- CONFIG HTTP connection diagnostics
#
# Clonker Designed by David Jacobson
# GitHub: https://github.com/djacobson/clonker-10000

"""Optional, bounded diagnostics for the CONFIG HTTP listener.

Tracks only the current connection. No sockets, request buffers, response
bodies, history, or filesystem writes are retained.

Disable WEB_DIAGNOSTICS_ENABLED for normal operation.
"""

import time

from clonker.system import logger


WEB_DIAGNOSTICS_ENABLED = True

_connection = None


def begin(now):
    """Start diagnostics for one accepted connection."""
    global _connection

    if not WEB_DIAGNOSTICS_ENABLED:
        _connection = None
        return

    _connection = {
        "started": now,
        "route": None,
        "request_bytes": 0,
        "response_bytes": 0,
        "build_ns": 0,
        "send_calls": 0,
        "send_ok": 0,
        "send_blocked": 0,
        "send_zero": 0,
        "last_send": None,
    }


def request(first_line, request_bytes):
    """Record the request line and received byte count."""
    if _connection is None:
        return

    # Keep the route identifier bounded.
    _connection["route"] = bytes(first_line[:96])
    _connection["request_bytes"] = request_bytes


def response(response_bytes, build_ns):
    """Record response size and construction time."""
    if _connection is None:
        return

    _connection["response_bytes"] = response_bytes
    _connection["build_ns"] = build_ns


def send_attempt():
    """Count one socket send attempt."""
    if _connection is not None:
        _connection["send_calls"] += 1


def send_blocked():
    """Count a send that raised EAGAIN."""
    if _connection is not None:
        _connection["send_blocked"] += 1


def send_zero():
    """Count a send returning zero bytes or None."""
    if _connection is not None:
        _connection["send_zero"] += 1


def send_success(now):
    """Record a successful socket send operation."""
    if _connection is None:
        return

    _connection["send_ok"] += 1
    _connection["last_send"] = now


def close(reason, sent_bytes):
    """Report and discard the current connection."""
    global _connection

    if _connection is None:
        return

    # Release the reference before logging, so even a logging
    # failure cannot leave connection history retained.
    stats = _connection
    _connection = None

    now = time.monotonic_ns()
    elapsed_ms = (now - stats["started"]) / 1_000_000

    last_send = stats["last_send"]
    if last_send is None:
        since_send = "none"
    else:
        since_send = "{:.1f}".format(
            (now - last_send) / 1_000_000
        )

    logger.info(
        "WEB DIAG: close={}, route={}, elapsed={:.1f}ms, "
        "request={}, response={}, sent={}".format(
            reason,
            stats["route"],
            elapsed_ms,
            stats["request_bytes"],
            stats["response_bytes"],
            sent_bytes,
        )
    )

    logger.info(
        "WEB DIAG: build={:.1f}ms, send_calls={}, "
        "send_ok={}, EAGAIN={}, send_zero={}, "
        "since_last_send={}ms".format(
            stats["build_ns"] / 1_000_000,
            stats["send_calls"],
            stats["send_ok"],
            stats["send_blocked"],
            stats["send_zero"],
            since_send,
        )
    )
