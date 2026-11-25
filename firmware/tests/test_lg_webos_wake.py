# THE CLONKER 10000
# LG webOS Wake-on-LAN experiment
#
# Run from the CircuitPython REPL with Wi-Fi connected.
# No production adapter dependencies.

import time
import wifi
import socketpool

# Enter the target TV's Ethernet MAC address.
MAC = "B0:37:95:D6:D4:9F"

BROADCAST = "192.168.50.255"
PORT = 9

if not wifi.radio.connected:
    raise RuntimeError("Wi-Fi is not connected")

mac_bytes = bytes(
    int(part, 16) for part in MAC.split(":")
)

if len(mac_bytes) != 6:
    raise ValueError("Invalid MAC address")

packet = b"\xff" * 6 + mac_bytes * 16

print("\n=== LG WAKE-ON-LAN TEST ===")
print("Local IP:", wifi.radio.ipv4_address)
print("Destination:", BROADCAST, PORT)
print("Packet size:", len(packet), "bytes")

pool = socketpool.SocketPool(wifi.radio)
sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

try:
    start = time.monotonic_ns()

    sent = sock.sendto(packet, (BROADCAST, PORT))

    elapsed = (time.monotonic_ns() - start) / 1000000

    print("Bytes transmitted:", sent)
    print("Transmission time: %.1f ms" % elapsed)

finally:
    sock.close()

print("Socket closed.")
print("Observe TV for wake-up.")
print("=== TEST COMPLETE ===")
