"""The web interface. Start it with ``meshpreflight web``."""

from .app import create_app

__all__ = ["create_app"]
