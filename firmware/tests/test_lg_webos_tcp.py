# LG webOS raw TCP connectivity test.
#
# Tests TCP connectivity independently of WebSocket
# negotiation, authentication, and pairing.
#
# No commands are transmitted to the televisions.

import time
import wifi
import socketpool

TARGETS = (
    ("Sunroom G1", "192.168.50.20"),
    ("Den C6H", "192.168.50.52"),
)

PORTS = (3000, 3001)
TIMEOUT = 5.0

print("\n=== LG webOS TCP Connectivity ===")
print("Wi-Fi connected:", wifi.radio.connected)
print("Pico IP:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)

passed = 0
failed = 0

for name, host in TARGETS:
    for port in PORTS:
        print("\n{} - {}:{}".format(name, host, port))

        sock = None
        start = time.monotonic()

        try:
            sock = pool.socket(
                pool.AF_INET,
                pool.SOCK_STREAM
            )
            sock.settimeout(TIMEOUT)

            print("Connecting TCP...")
            sock.connect((host, port))

            elapsed = (time.monotonic() - start) * 1000

            print("PASS: Connected in {:.1f} ms".format(elapsed))
            passed += 1

        except Exception as error:
            elapsed = (time.monotonic() - start) * 1000

            print("FAIL: {:.1f} ms".format(elapsed))
            print("Error:", repr(error))
            failed += 1

        finally:
            if sock is not None:
                sock.close()
                print("Socket closed.")

        time.sleep(1)

print("\n=== RESULTS ===")
print("Passed:", passed)
print("Failed:", failed)
print("Test complete.")
