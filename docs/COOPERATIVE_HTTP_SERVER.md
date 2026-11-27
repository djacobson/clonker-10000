# Cooperative HTTP Server Design

> A small HTTP server should never make the rest of a microcontroller wait unnecessarily.

## Purpose

This document describes the design principles behind the cooperative HTTP server used by [THE CLONKER 10000](https://github.com/djacobson/clonker-10000).

Although the implementation is specific to CircuitPython and the Raspberry Pi Pico 2 W, the principles apply to other resource-constrained embedded systems.

The goal is not to build a general-purpose web server. It is to provide reliable configuration and management interfaces while preserving responsiveness to physical controls and other time-sensitive work.

## 1. The Cooperative Scheduling Model

Clonker uses a single-threaded cooperative dispatcher.

The main loop services several responsibilities:

- Physical controls and input events.
- The remote-command queue and device adapters.
- OLED feedback.
- HTTP configuration and management requests.
- Periodic maintenance and diagnostics.

Each component must return control promptly so the dispatcher can continue servicing other responsibilities.

The HTTP server is therefore implemented as a stateful, nonblocking service that advances incrementally through repeated `poll()` calls.

A typical HTTP connection progresses through:

1. Accept a TCP connection.
2. Receive request bytes.
3. Parse and validate the complete HTTP request.
4. Prepare the response.
5. Send response bytes incrementally.
6. Close the connection and release resources.

These stages do not need to complete during one scheduler iteration.

**Key principle:** Network I/O should make bounded progress and return control to the dispatcher.

This is cooperative scheduling, not parallel execution. Synchronous operations elsewhere in the application can still introduce latency.

## 2. Nonblocking Socket Operations

Clonker uses nonblocking sockets for its HTTP listener and active client.

The server maintains connection state between polling
iterations rather than intentionally waiting inside
a blocking read or write.

Native socket implementations may nevertheless
introduce blocking behavior outside the application's
direct control.

Important characteristics:

| Characteristic | Clonker implementation |
|---|---|
| HTTP protocol | HTTP/1.1 over plain TCP |
| Listening backlog | 2 |
| Active clients | 1 |
| Socket mode | Nonblocking |
| Receive operation | Up to 128 bytes per poll |
| Send operation | Up to 1,024 bytes per poll |
| Minimum interval between send attempts | 50 ms |
| Completed-response close grace | 250 ms |
| Maximum request | 18,432 bytes |
| Maximum headers | 2,048 bytes |
| Idle, zero-byte client timeout | 200 ms |
| Active connection inactivity timeout | 4 seconds |
| Response connection policy | `Connection: close` |

These limits are design choices, not universal recommendations.

They balance browser compatibility, available RAM, implementation complexity, and dispatcher responsiveness.

### Partial reads and writes

A nonblocking socket operation may transfer fewer bytes than requested.

A correct implementation must preserve its progress and continue during a later polling iteration.

For sending:

- Track the number of response bytes already transmitted.
- Advance the offset only by the number actually sent.
- Treat temporary socket unavailability as a reason to yield.
- Close the connection only after completing the response or encountering an error or timeout.

The same general principle applies to receiving requests.

## 3. Streaming HTML from Flash

One of Clonker's most valuable improvements was streaming HTML directly from flash storage rather than assembling entire pages in RAM.

This provides two important benefits.

**Lower memory consumption**

Large HTML pages do not require equally large temporary heap allocations.

Instead, the server reads and transmits small chunks.

**Better scheduling behavior**

Between chunks, the HTTP service returns control to the main dispatcher.

This allows other tasks to continue operating while the browser downloads a page.

The current implementation uses 1,024-byte send
chunks, with cooperative pacing between send attempts.

Streaming significantly reduced the memory pressure and page-freezing problems encountered during development.

However, response preparation and filesystem operations may still contain synchronous work. Streaming does not automatically make every operation nonblocking.

## 4. Browser Connections Are Not Always HTTP Requests

Modern browsers may establish TCP connections before they have an HTTP request ready to send.

This behavior can arise from connection reuse strategies, speculative preconnecting, or other browser networking decisions.

Consequently:

**An accepted TCP connection does not guarantee that an HTTP request will follow.**

An embedded server may observe:

1. A successful TCP connection.
2. No incoming request bytes.
3. A period of inactivity.
4. A socket timeout and closure.

This is not necessarily a malfunction.

### Clonker's approach

Clonker permits only one active HTTP client.

An idle browser connection therefore temporarily occupies a resource that another request might need.

To limit that impact, Clonker uses a short 200 ms timeout for connections that have neither received request bytes nor begun sending a response.

Connections making progress use the longer four-second inactivity timeout.

The short timeout is intentional: an unused connection should not monopolize the server.

### Important distinction

The browser decides when to open connections.

The server controls how long it retains them and how it handles incomplete requests.

A zero-byte timeout alone does not prove that the browser was speculatively preconnecting, nor does it prove the server caused the connection.

## 5. HTTP Response Framing and Cleanup

Clonker uses straightforward HTTP/1.1 response framing.

Responses include:

- An HTTP status line.
- An explicit `Content-Length`.
- `Connection: close`.
- A complete response body.

Persistent HTTP connections are intentionally unsupported.

This simplifies the connection lifecycle and avoids keeping idle client sockets open between requests.

When a connection completes, fails, or times out, the server releases its associated resources.

Cleanup includes closing the socket, closing any active response file, and clearing references to connection-specific buffers and state.

Connection ownership is registered immediately after
acceptance. Connection-specific references are cleared
before potentially failing cleanup operations.

Memory allocation failures discard the active client,
release its response buffers and file resources,
and invoke garbage collection.

The listening socket remains available for subsequent
requests when possible.

### Dynamic response memory management

Dynamic HTTP responses retain separate header and
encoded payload buffers.

The server transmits the header first, then advances
to the payload using the existing cooperative
response state.

This avoids allocating another contiguous buffer
containing the complete header and payload.

For a configuration response of approximately 9.5 KB,
this eliminates an unnecessary allocation of
approximately the same size.

Temporary configuration references are released
after JSON serialization.

The receive path also reuses a small receive buffer
and retains the validated expected request length
rather than repeatedly parsing POST headers.

**Key principle:** Every connection must have a bounded lifetime and a reliable cleanup path.

## 6. Integration with the Cooperative Dispatcher

The HTTP server is only one participant in Clonker's scheduler.

Physical-control processing and remote-command execution must remain responsive even while the configuration interface is active.

The design therefore emphasizes:

- Small, bounded socket operations.
- Minimal work per HTTP poll.
- Persistent state across iterations.
- Explicit timeout handling.
- Predictable resource cleanup.
- Scheduling priorities that favor the device's primary purpose.

### What can still block?

Cooperative scheduling does not eliminate all blocking behavior.

Examples include:

- Filesystem writes.
- JSON parsing or serialization.
- Response preparation.
- Synchronous outbound HTTP commands to controlled devices.
- Other lengthy application operations.

These operations must be evaluated separately from inbound HTTP socket handling.

The goal is not necessarily to eliminate every blocking operation, but to keep latency acceptable without introducing unnecessary complexity.

### Native socket behavior

Nonblocking socket configuration does not guarantee
that every native socket operation returns promptly.

Inspection of CircuitPython 10.3.1's Raspberry Pi
socket implementation revealed that `lwip_tcp_send()`
can retry `tcp_write()` following `ERR_MEM` for
approximately ten seconds, even on a nonblocking socket.

This is consistent with the recurring ten-second
HTTP send stalls observed during Clonker development.

The exact native resource exhaustion mechanism has
not been established.

Cooperative send pacing and delayed connection closure
are retained as conservative transport measures,
not as proven corrections for the underlying defect.

See [Firmware Networking](FIRMWARE_NETWORK.md)
for the investigation and operational limitations.

## 7. Diagnostics and Endurance Testing

Useful HTTP diagnostics distinguish between:

- TCP connections accepted.
- Request bytes received.
- Requests parsed successfully.
- Response bytes transmitted.
- Completed responses.
- Client timeouts.
- Socket errors.
- Connection cleanup.

In particular, a timeout with zero request bytes and zero response bytes should be distinguished from a partially received or partially transmitted HTTP exchange.

These conditions have different diagnostic implications.

### What endurance testing demonstrated

During Clonker's Chapter 9 testing, the firmware maintained stable free-memory readings through more than 21 hours of operation.

A subsequent remote-control action completed successfully.

This supports the stability of the overall cooperative application during the observed test.

It does not prove that every HTTP path, network failure, or concurrency scenario has been exhaustively tested.

### Diagnostic overhead

Detailed socket diagnostics are valuable during investigation but may themselves introduce execution overhead.

They should be lightweight, optional, and removable from normal operation without changing the server's functional behavior.

## 8. Design Tradeoffs

| Design choice | Benefit | Tradeoff |
|---|---|---|
| One active client | Low memory usage and simple state management | Concurrent requests must wait |
| Nonblocking I/O | Preserves cooperative scheduling | Requires explicit state tracking |
| Short idle timeout | Quickly releases unused sockets | May reject unusually delayed requests |
| Flash streaming | Low RAM usage and incremental sending | Requires careful file lifecycle handling |
| Explicit connection close | Simple HTTP lifecycle | New TCP connection for subsequent requests |
| Fixed-size I/O chunks | Predictable per-poll work | More scheduler iterations per response |
| Synchronous outbound commands | Simpler device-adapter implementation | Can temporarily delay other tasks |

No single choice is universally optimal.

For an embedded remote-control device with modest configuration traffic, this combination is a reasonable compromise.

## 9. Lessons for Future Projects

When designing another cooperative HTTP server:

1. **Protect the application's primary purpose.** HTTP management should not dominate time-sensitive device behavior.
2. **Use nonblocking sockets where practical.** Avoid waiting for a browser that may never send data.
3. **Preserve connection state across scheduler iterations.** Do not assume a complete request or response fits in one operation.
4. **Bound memory and work per iteration.** Limit request sizes, buffers, and socket transfers.
5. **Stream large static resources.** Avoid unnecessary whole-page heap allocations.
6. **Distinguish idle connections from failed requests.** Zero-byte timeouts may be routine browser behavior.
7. **Use explicit response framing and cleanup.** Keep the connection lifecycle understandable.
8. **Measure before optimizing.** Complexity should solve an observed problem rather than a hypothetical one.
9. **Test both idle endurance and active behavior.** Stable memory alone does not establish full application reliability.
10. **Keep the dispatcher cooperative.** A technically correct HTTP server is not useful if it makes the device's physical controls unresponsive.

## Conclusion

Clonker's HTTP server succeeds by doing relatively little at any one time.

It accepts a connection, makes bounded progress, preserves its state, and returns control to the cooperative dispatcher.

Browsers may be impatient, speculative, or unnecessarily enthusiastic about opening connections. The embedded server does not need to accommodate every such behavior indefinitely.

Its responsibility is to process valid requests reliably, release unused resources promptly, and avoid interfering with the device's primary functions.

**The best embedded HTTP server is not necessarily the fastest one. It is the one that gets its work done without getting in everybody else's way.**

---

## Implementation References

- [Clonker HTTP server](../firmware/clonker/net/web.py)
- [HTTP diagnostics](../firmware/clonker/net/web_diag.py)
- [Main cooperative dispatcher](../firmware/clonker/main.py)
- [Firmware networking documentation](FIRMWARE_NETWORK.md)
- [System architecture](ARCHITECTURE.md)

---

*Less sleek. More CLONK.*
