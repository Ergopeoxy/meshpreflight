"""The plug-in system for checks.

Each check is a small class that inherits from :class:`Check` and answers two
questions: "do you apply to this mesh?" and "what did you find?". Adding one needs no
change anywhere else, because the ``@register_check`` decorator puts it on the list
that the runner uses. See ``docs/extending.md`` for a worked example.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np

from ..expectations import Expectations
from ..findings import Finding
from ..mesh import Mesh
from ..quality import QualityLimits, compute_quality


@dataclass
class CheckContext:
    """Everything a check may look at, shared by all checks in one run.

    Expensive results, such as quality metrics, are computed once on first use.
    """

    mesh: Mesh
    expect: Expectations = field(default_factory=Expectations)
    limits: QualityLimits = field(default_factory=QualityLimits)

    @cached_property
    def quality(self) -> dict[str, np.ndarray]:
        return compute_quality(self.mesh)


class Check(ABC):
    """Base class for all checks.

    Class attributes:
        id: Short unique name, used to select or disable the check.
        title: Human-readable name for reports.
        description: What the check does and why it matters to a simulation.
    """

    id: str = ""
    title: str = ""
    description: str = ""

    def skip_reason(self, ctx: CheckContext) -> str | None:
        """Return why this check cannot run on this mesh, or ``None`` if it can.

        Reports list skipped checks with their reasons, so "not checked" can never
        be mistaken for "checked and fine".
        """
        return None

    @abstractmethod
    def run(self, ctx: CheckContext) -> list[Finding]:
        """Inspect the mesh and return findings. An empty list means nothing found."""


#: Every registered check, in the order they run.
CHECK_REGISTRY: list[type[Check]] = []


def register_check(cls: type[Check]) -> type[Check]:
    """Class decorator that adds a check to :data:`CHECK_REGISTRY`."""
    if not cls.id:
        raise ValueError(f"{cls.__name__} must define an id")
    if any(existing.id == cls.id for existing in CHECK_REGISTRY):
        raise ValueError(f"A check with id {cls.id!r} is already registered")
    CHECK_REGISTRY.append(cls)
    return cls
