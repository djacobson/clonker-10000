# The Clonker 10000
# Chapter 3, Phase B1 -- HTTP transport bench test

from clonker.net import http_transport

TESTS = (
    (
        "Roku device information",
        "192.168.50.28:8060",
        "GET",
        "/query/device-info",
    ),
    (
        "Denon main-zone status",
        "192.168.50.44:8080",
        "GET",
        "/goform/formMainZone_MainZoneXml.xml",
    ),
    (
        "Unreachable LAN address",
        "192.168.50.100:8060",
        "GET",
        "/query/device-info",
    ),
)

for label, endpoint, method, path in TESTS:
    print()
    print("=" * 48)
    print("TEST:", label)

    try:
        result = http_transport.send(
            endpoint, method, path
        )
        print("SUCCESS:", result)

    except Exception as error:
        print("ERROR:", repr(error))

print()
print("B1 bench tests complete")
