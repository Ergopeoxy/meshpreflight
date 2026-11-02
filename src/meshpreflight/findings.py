"""The vocabulary of a report: how severe something is, and what was found."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class Severity(str, Enum):
    """How much a finding should worry you.

    * ``ERROR``: the mesh is broken for almost any FEM use, or contradicts what you
      said you expected. Do not trust results until this is resolved.
    * ``WARNING``: suspicious, but it can be legitimate. For example, a shell model
      really is an open surface. Look at it and decide.
    * ``INFO``: worth knowing, and rarely a problem.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    """One thing a check noticed.

    Attributes:
        code: Stable identifier such as ``"TAG_MISSING"``. Tests and scripts should
            rely on this, since the message wording may improve over time.
        severity: See :class:`Severity`.
        message: What was found, stated in plain language.
        hint: What usually causes this and how to fix it.
        count: How many items are affected.
        cells: Maps a cell kind to indices of the affected cells, for highlighting.
        points: Indices of the affected points, for highlighting.
    """

    code: str
    severity: Severity
    message: str
    hint: str = ""
    count: int = 0
    cells: dict[str, np.ndarray] = field(default_factory=dict)
    points: np.ndarray | None = None

    def to_dict(self) -> dict:
        """Plain data for JSON. Index lists are left out to keep responses small."""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "hint": self.hint,
            "count": int(self.count),
        }
