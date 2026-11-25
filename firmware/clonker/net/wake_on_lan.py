# The Clonker 10000
# clonker/net/wake_on_lan.py
#
# Chapter 13 -- Generic Wake-on-LAN transport
#
# Clonker Designed by David Jacobson

"""Transmit Wake-on-LAN magic packets.

Commands are validated by the configuration engine.

Successful transmission does not confirm that the
target device has powered on.
"""

import wifi
import socketpool


SOCKET_TIMEOUT = 0.5
PACKET_SIZE = 102


def send(command):
    """Transmit one magic packet using a temporary UDP socket.

    Raises on transmission failure.
    No retries or response tracking.
    """

    mac_bytes = bytes(
        int(part, 16)
        for part in command["mac"].split(":")
    )

    packet = b"\xff" * 6 + mac_bytes * 16

    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

    try:
        sock.settimeout(SOCKET_TIMEOUT)

        sent = sock.sendto(
            packet,
            (command["broadcast"], command["port"])
        )

        if sent != PACKET_SIZE:
            raise RuntimeError(
                "Incomplete Wake-on-LAN transmission"
            )

    finally:
        sock.close()

    return sent
