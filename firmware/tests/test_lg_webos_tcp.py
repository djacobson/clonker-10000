# LG webOS TCP and WSS connectivity test.
#
# Stage 1: Raw TCP connectivity.
# Stage 2: TLS negotiation.
# Stage 3: WebSocket upgrade over TLS.
#
# No pairing, authentication, or TV control commands.

import time
import gc
import wifi
import socketpool

TARGETS = (
    ("Sunroom G1", "192.168.50.20"),
    ("Den C6H", "192.168.50.52"),
)

PORTS = (3000, 3001)
TIMEOUT = 5.0
MAX_HEADER = 4096

pool = socketpool.SocketPool(wifi.radio)


def elapsed_ms(start):
    return (time.monotonic() - start) * 1000


def tcp_test(host, port):
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

        print("PASS: TCP {:.1f} ms".format(
            elapsed_ms(start)
        ))
        return True

    except Exception as error:
        print("FAIL: TCP {:.1f} ms".format(
            elapsed_ms(start)
        ))
        print("Error:", repr(error))
        return False

    finally:
        if sock is not None:
            sock.close()


def wss_test(host):
    raw = None
    secure = None
    context = None
    stage = "SSL initialization"

    gc.collect()
    print("Free heap before:", gc.mem_free())

    try:
        import ssl
        import os
        import binascii

        context = ssl.create_default_context()

        # Local diagnostic only.
        # LG may present a self-signed certificate.
        context.check_hostname = False

        # CircuitPython may not expose verify_mode.
        if hasattr(context, "verify_mode"):
            if hasattr(ssl, "CERT_NONE"):
                context.verify_mode = ssl.CERT_NONE
                print("Certificate verification disabled")
        else:
            print("Using CircuitPython SSL verification policy")

        stage = "Socket creation"

        raw = pool.socket(
            pool.AF_INET,
            pool.SOCK_STREAM
        )
        raw.settimeout(TIMEOUT)

        stage = "TLS wrap"
        start = time.monotonic()

        secure = context.wrap_socket(
            raw,
            server_hostname=host
        )
        secure.settimeout(TIMEOUT)

        print("SSL wrapped: {:.1f} ms".format(
            elapsed_ms(start)
        ))

        stage = "TCP/TLS connect"
        start = time.monotonic()

        secure.connect((host, 3001))

        print("PASS: TCP/TLS {:.1f} ms".format(
            elapsed_ms(start)
        ))
        print("Free heap connected:", gc.mem_free())

        stage = "WebSocket request"

        key = binascii.b2a_base64(
            os.urandom(16)
        ).strip().decode()

        request = (
            "GET / HTTP/1.1\r\n"
            "Host: {}:3001\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).format(host, key).encode()

        start = time.monotonic()

        offset = 0

        while offset < len(request):
            sent = secure.send(request[offset:])

            if not sent:
                raise RuntimeError("Incomplete send")

            offset += sent

        stage = "WebSocket response"

        response = bytearray()
        buf = bytearray(256)

        while b"\r\n\r\n" not in response:
            if elapsed_ms(start) > TIMEOUT * 1000:
                raise RuntimeError("Upgrade timeout")

            count = secure.recv_into(buf)

            if not count:
                raise RuntimeError("Connection closed")

            response.extend(buf[:count])

            if len(response) > MAX_HEADER:
                raise RuntimeError("Header too large")

        header = bytes(response).split(
            b"\r\n\r\n", 1
        )[0]

        print("WebSocket response:")
        print(header.decode())

        status = header.split(b"\r\n", 1)[0]

        if not status.startswith(b"HTTP/1.1 101 "):
            raise RuntimeError("Upgrade rejected")

        print("PASS: WSS upgrade {:.1f} ms".format(
            elapsed_ms(start)
        ))

        return True

    except Exception as error:
        print("FAIL stage:", stage)
        print("Error:", repr(error))
        return False

    finally:
        try:
            if secure is not None:
                secure.close()
            elif raw is not None:
                raw.close()

        except Exception as error:
            print("Close error:", repr(error))

        secure = None
        raw = None
        context = None

        gc.collect()
        print("Free heap after:", gc.mem_free())
        print("Socket cleanup complete.")


print("\n=== LG webOS TCP / WSS Connectivity ===")
print("Wi-Fi connected:", wifi.radio.connected)
print("Pico IP:", wifi.radio.ipv4_address)

tcp_passed = 0
tcp_failed = 0
wss_passed = 0
wss_failed = 0

print("\n=== STAGE 1: RAW TCP ===")

for name, host in TARGETS:
    for port in PORTS:
        print("\n{} - {}:{}".format(
            name, host, port
        ))

        if tcp_test(host, port):
            tcp_passed += 1
        else:
            tcp_failed += 1

        time.sleep(1)

print("\n=== STAGE 2: TLS / WSS ===")

for name, host in TARGETS:
    print("\n{} - wss://{}:3001".format(
        name, host
    ))

    if wss_test(host):
        wss_passed += 1
    else:
        wss_failed += 1

    time.sleep(1)

print("\n=== RESULTS ===")
print("TCP passed:", tcp_passed)
print("TCP failed:", tcp_failed)
print("WSS passed:", wss_passed)
print("WSS failed:", wss_failed)
print("Test complete.")
