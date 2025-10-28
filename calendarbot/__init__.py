"""Calendar Bot - ICS Calendar Display Bot for Raspberry Pi with e-ink display.

.. deprecated:: 1.0.0
   The `calendarbot` package is archived and no longer actively maintained.
   Use `calendarbot_lite` for new development.

   See calendarbot/DEPRECATED.md for more information.
"""

import warnings

warnings.warn(
    "The 'calendarbot' package is deprecated and archived. "
    "Please use 'calendarbot_lite' for new development. "
    "See calendarbot/DEPRECATED.md for details.",
    DeprecationWarning,
    stacklevel=2
)

__version__ = "1.0.0"
__author__ = "CalendarBot Team"
__email__ = "support@calendarbot.local"
__description__ = "[DEPRECATED] ICS Calendar Display Bot for Raspberry Pi with e-ink display and web interface"

# Package metadata
__all__ = [
    "__author__",
    "__description__",
    "__email__",
    "__version__",
]
