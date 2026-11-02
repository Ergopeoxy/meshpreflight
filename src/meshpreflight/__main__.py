"""Allows ``python -m meshpreflight`` as an alternative to the ``meshpreflight`` command."""

import sys

from .cli import main

sys.exit(main())
