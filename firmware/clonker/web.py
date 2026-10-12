# The Clonker 10000
# clonker/web.py
#
# Initial web interface experiment.
# No network listener yet.

from clonker import clock


def clock_page():
    """Generate a simple HTML clock status page."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Clonker 10000</title>
</head>
<body>
    <h1>THE CLONKER 10000</h1>
    <h2>System Clock</h2>
    <p>Clock source: {}</p>
    <p>Current time: {}</p>
</body>
</html>""".format(
        clock.source(),
        clock.timestamp()
    )
