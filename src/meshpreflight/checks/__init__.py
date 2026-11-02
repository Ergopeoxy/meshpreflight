"""All built-in checks.

Importing the modules below is what runs their ``@register_check`` decorators, so the
order of imports here is the order the checks run in.
"""

from . import elements, scale, tags, topology  # noqa: F401
from .base import CHECK_REGISTRY, Check, CheckContext, register_check

__all__ = ["CHECK_REGISTRY", "Check", "CheckContext", "register_check"]
