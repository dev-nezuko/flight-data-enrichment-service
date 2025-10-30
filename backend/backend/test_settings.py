"""Settings for the test run: debug mode supplies a throwaway signing key."""

import os

os.environ.setdefault("DEBUG", "true")

from .settings import *  # noqa: E402,F403
