# The Clonker 10000
# firmware/tests/socket_send_stall.py
#
# Experiment 4: cooperative POST -> GET, no flash writes.
# CircuitPython 10.3.1 / Raspberry Pi Pico 2 W.
#
# REPL:
# exec(open("/tests/socket_send_stall.py").read())
#
# Ctrl+C to stop.

import os
import time
import errno
import json
import gc
import wifi
import socketpool

PORT = 9091
CHUNK_SIZE = 512
POLL_INTERVAL_S = 0.001
SLOW_SEND_NS = 20_000_000
CLIENT_TIMEOUT_NS = 4_000_000_000
IDLE_TIMEOUT_NS = 200_000_000
MAX_REQUEST_BYTES = 10240

TEST_PAGE = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width">
<title>Clonker Socket Test</title>
</head>
<body>
<h2>Clonker POST / GET Test</h2>
<p>No configuration or flash writes.</p>
<label>Cycles:
<input id="cycles" type="number" value="20" min="1" max="100">
</label>
<button id="start">Start</button>
<pre id="output">Ready.</pre>
<script>
const output = document.getElementById("output");
const button = document.getElementById("start");

button.onclick = async () => {
    button.disabled = true;
    const cycles = Number(document.getElementById("cycles").value);
    let passed = 0;
    output.textContent = "Running...\\n";

    try {
        for (let i = 1; i <= cycles; i++) {
            const config = {
                version: 4,
                rooms: {
                    "room-1": {name: "Den", actions: ["Movie", "Music"]},
                    "room-2": {name: "Sunroom", actions: ["Movie"]},
                    "room-3": {name: "Test " + i, actions: []}
                },
                padding: "P".repeat(3500)
            };

            const post = await fetch("/api/config", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(config),
                cache: "no-store"
            });

            if (!post.ok) throw Error("POST HTTP " + post.status);
            const ack = await post.json();
            if (!ack.saved) throw Error("POST not acknowledged");

            const get = await fetch("/api/config", {
                cache: "no-store"
            });

            if (!get.ok) throw Error("GET HTTP " + get.status);
            const data = await get.json();
            if (!data.rooms) throw Error("Invalid GET response");

            passed++;
            output.textContent = "Passed " + passed +
                " / " + cycles + " cycles";
        }
        output.textContent += "\\nCOMPLETE";
    } catch (error) {
        output.textContent += "\\nFAILED: " + error.message;
    } finally {
        button.disabled = false;
    }
};
</script>
</body>
</html>
"""

def make_http(body, content_type="application/json",
              status="200 OK"):
    if isinstance(body, str):
        body = body.encode("utf-8")
    header = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ).format(status, content_type, len(body))
    return header.encode("utf-8") + body


def build_config():
    config = {
        "version": 4,
        "rooms": {
            "room-1": {
                "name": "Den",
                "actions": ["Movie", "Music", "Vinyl"]
            },
            "room-2": {
                "name": "Sunroom",
                "actions": ["Movie", "Music"]
            },
            "room-3": {
                "name": "Test Room",
                "actions": []
            }
        },
        "padding": "X" * 4950
    }
    return make_http(json.dumps(config))


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

client = None
request = None
response = None
sent = 0
last_activity = 0
started = 0
requests = 0
completed = 0
timeouts = 0
slow_sends = 0
max_send_ns = 0
send_calls = 0
route = ""


def would_block(error):
    return error.errno == errno.EAGAIN


def close_client(reason):
    global client, request, response, sent
    global completed, timeouts

    if client is None:
        return

    if reason == "complete":
        completed += 1
    elif reason == "timeout":
        timeouts += 1

    print(
        "#{} {} {} sent={}/{} calls={} "
        "max_send={:.1f}ms slow={} total={:.1f}ms".format(
            requests,
            route,
            reason,
            sent,
            len(response) if response is not None else 0,
            send_calls,
            max_send_ns / 1_000_000,
            (1 if slow_sends else 0),
            (time.monotonic_ns() - started) / 1_000_000
        )
    )

    try:
        client.close()
    except OSError:
        pass

    client = None
    request = None
    response = None
    sent = 0


def complete_request(data):
    """Return True only after headers AND POST body arrive."""
    boundary = data.find(b"\r\n\r\n")
    if boundary < 0:
        return False

    headers = bytes(data[:boundary]).decode("utf-8")
    first_line = headers.split("\r\n", 1)[0]

    length = 0
    for line in headers.split("\r\n")[1:]:
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
            break

    if length < 0 or length > 8192:
        raise ValueError("Invalid Content-Length")

    if first_line.startswith("POST ") and length == 0:
        raise ValueError("Missing POST body")

    return len(data) >= boundary + 4 + length


def build_for_request(data):
    global route

    boundary = data.find(b"\r\n\r\n")
    headers = bytes(data[:boundary]).decode("utf-8")
    route = headers.split("\r\n", 1)[0]

    if route.startswith("GET / "):
        return make_http(TEST_PAGE, "text/html")

    if route.startswith("GET /api/config "):
        return build_config()

    if route.startswith("POST /api/config "):
        body = bytes(data[boundary + 4:])
        parsed = json.loads(body.decode("utf-8"))
        if not isinstance(parsed, dict) or "rooms" not in parsed:
            raise ValueError("Invalid configuration")

        return make_http('{"saved":true}')

    return make_http(
        '{"error":"Not found"}',
        status="404 Not Found"
    )


def poll():
    global client, request, response, sent
    global last_activity, started, requests
    global send_calls, slow_sends, max_send_ns
    global route

    now = time.monotonic_ns()

    if client is None:
        try:
            new_client, address = listener.accept()
        except OSError as error:
            if would_block(error):
                return
            raise

        new_client.settimeout(0)
        client = new_client
        request = bytearray()
        response = None
        sent = 0
        send_calls = 0
        slow_sends = 0
        max_send_ns = 0
        route = "(receiving)"
        last_activity = now
        started = now
        requests += 1
        return

    silent = response is None and len(request) == 0
    timeout_ns = (
        IDLE_TIMEOUT_NS if silent
        else CLIENT_TIMEOUT_NS
    )

    if now - last_activity > timeout_ns:
        close_client("timeout")
        return

    if response is None:
        buf = bytearray(CHUNK_SIZE)

        try:
            count = client.recv_into(buf)
        except OSError as error:
            if would_block(error):
                return
            print("Receive error:", error)
            close_client("receive_error")
            return

        if count == 0:
            close_client("peer_closed")
            return

        request.extend(memoryview(buf)[:count])
        last_activity = now

        if len(request) > MAX_REQUEST_BYTES:
            close_client("request_too_large")
            return

        try:
            if not complete_request(request):
                return
            response = build_for_request(request)
        except (ValueError, UnicodeError, TypeError) as error:
            print("Request error:", error)
            response = make_http(
                '{"error":"Bad request"}',
                status="400 Bad Request"
            )

        print(
            "BUILD #{} bytes={} free={}".format(
                requests, len(response), gc.mem_free()
            )
        )

        request = None
        sent = 0
        return

    if sent >= len(response):
        close_client("complete")
        return

    chunk = memoryview(response)[sent:sent + CHUNK_SIZE]
    send_calls += 1
    send_started = time.monotonic_ns()

    try:
        count = client.send(chunk)
    except OSError as error:
        if would_block(error):
            return
        print("Send error:", error)
        close_client("send_error")
        return
    finally:
        duration = time.monotonic_ns() - send_started
        if duration > max_send_ns:
            max_send_ns = duration
        if duration > SLOW_SEND_NS:
            slow_sends += 1
            print(
                "SLOW SEND #{} {} sent={} {:.1f}ms".format(
                    requests, route, sent,
                    duration / 1_000_000
                )
            )

    if count is None or count <= 0:
        return

    sent += count
    last_activity = now

    if sent >= len(response):
        close_client("complete")


print("Clonker POST/GET socket experiment ready")
print("Open http://{}:{}".format(
    wifi.radio.ipv4_address, PORT
))
print("No filesystem writes")

try:
    while True:
        poll()
        time.sleep(POLL_INTERVAL_S)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    if client is not None:
        try:
            client.close()
        except OSError:
            pass

    listener.close()
    print(
        "SUMMARY requests={} completed={} timeouts={}".format(
            requests, completed, timeouts
        )
    )
