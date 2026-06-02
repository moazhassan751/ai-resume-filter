"""Compatibility shim for the runtime data service package.

The live implementation sits in the top-level `services` package. This module
keeps existing imports like `app.services.data_service` working.
"""

from services.data_service import *  # noqa: F401,F403
