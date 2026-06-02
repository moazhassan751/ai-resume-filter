"""Compatibility shim for the async MongoDB helpers.

The live implementation sits in `app.services.db`. This module keeps the
older `app.db.mongo` import path working.
"""

from app.services.db import *  # noqa: F401,F403
