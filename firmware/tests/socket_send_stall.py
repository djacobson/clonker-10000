# The Clonker 10000 -- socket send stall experiment
# firmware/tests/socket_send_stall.py
#
# Standalone CircuitPython 10.3.1 / Pico 2 W test.
# Stop with Ctrl+C.

import os
import time
import wifi
import socketpool
import errno

PORT = 9091
CHUNK_SIZE = 512
BODY_SIZE = 5300
SLOW_SEND_NS = 20_000_000

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

if not wifi.radio.connected:
    if not ssid:
        raise RuntimeError("Wi-Fi credentials unavailable")
    wifi.radio.connect(ssid, password)

pool = socketpool.SocketPool(wifi.radio)
listener = pool.socket(pool.AF_INET, pool.SOCK_STREAM)

try:
    listener.setsockopt(
        pool.SOL_SOCKET, pool.SO_REUSEADDR, 1
    )
except (AttributeError, OSError):
    pass

listener.bind(("0.0.0.0", PORT))
listener.listen(2)
listener.settimeout(0)

body = b"X" * BODY_SIZE
header = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/plain\r\n"
    "Content-Length: {}\r\n"
    "Cache-Control: no-store\r\n"
    "Connection: close\r\n\r\n"
).format(len(body)).encode("utf-8")

response = header + body
requests = 0

print("Socket stall test ready")
print("Address: http://{}:{}".format(
    wifi.radio.ipv4_address, PORT
))
print("Response bytes:", len(response))

try:
    while True:
        try:
            client, address = listener.accept()
        except OSError as error:
            if error.errno == errno.EAGAIN:
                time.sleep(0.001)
                continue
            raise

        requests += 1
        sent = 0
        max_send_ns = 0
        slow_sends = 0
        started = time.monotonic_ns()

        client.settimeout(0)

        try:
            # Receive the browser's request.
            request = bytearray()

            while b"\r\n\r\n" not in request:
                try:
                    data = client.recv(512)
                except OSError as error:
                    if error.errno == errno.EAGAIN:
                        time.sleep(0.001)
                        continue
                    raise

                if not data:
                    break

                request.extend(data)

                if len(request) > 2048:
                    break

            # Send exactly one bounded chunk per iteration.
            while sent < len(response):
                chunk = memoryview(response)[
                    sent:sent + CHUNK_SIZE
                ]

                send_started = time.monotonic_ns()

                try:
                    count = client.send(chunk)
                except OSError as error:
                    if error.errno == errno.EAGAIN:
                        time.sleep(0.001)
                        continue
                    raise
                finally:
                    elapsed = (
                        time.monotonic_ns() - send_started
                    )
                    if elapsed > max_send_ns:
                        max_send_ns = elapsed
                    if elapsed > SLOW_SEND_NS:
                        slow_sends += 1
                        print(
                            "SLOW SEND: {:.1f}ms".format(
                                elapsed / 1_000_000
                            )
                        )

                if count is None or count <= 0:
                    time.sleep(0.001)
                    continue

                sent += count
                time.sleep(0.001)

        except OSError as error:
            print("Socket error:", error)

        finally:
            try:
                client.close()
            except OSError:
                pass

            print(
                "Request {}: sent={}/{}, "
                "max_send={:.1f}ms, slow={}, "
                "total={:.1f}ms".format(
                    requests,
                    sent,
                    len(response),
                    max_send_ns / 1_000_000,
                    slow_sends,
                    (
                        time.monotonic_ns() - started
                    ) / 1_000_000
                )
            )

finally:
    listener.close()
