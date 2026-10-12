# The Clonker 10000
# clonker/web.py
#
# Web interface support.
# HTML lives in the clonker/www directory.
#
# No HTTP listener yet.

import os

from clonker import clock
from clonker import logger


WEB_ROOT = os.path.dirname(__file__) + "/www"


def clock_page():
    """Load the Clonker home page from disk."""
    path = WEB_ROOT + "/index.html"

    with open(path, "r") as file:
        return file.read()


def clock_status():
    """Return current clock information."""
    return {
        "source": clock.source(),
        "timestamp": clock.timestamp(),
    }
