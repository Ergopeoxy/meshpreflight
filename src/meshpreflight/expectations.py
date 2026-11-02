"""What you believe should be true about a mesh, written down.

A file cannot tell a checker that it was meant to have an ``"inlet"`` or be 2 metres
long. Only you know that. Stating it here turns vague worries into exact comparisons,
and the more you state, the more the checks can catch.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TagExpectation:
    """One region that must exist.

    Attributes:
        name: The tag's name, such as ``"inlet"``.
        dim: Its dimension: ``1`` for a boundary curve, ``2`` for a surface,
            ``3`` for a solid region.
        measure: Optional expected length, area or volume.
    """

    name: str
    dim: int
    measure: float | None = None


@dataclass
class Expectations:
    """Everything a check may compare the mesh against. All fields are optional.

    Attributes:
        tags: The regions that must exist.
        volume: Expected total volume.
        area: Expected total area (surface area, or plain area in 2D).
        size: Expected largest extent of the bounding box.
        rel_tol: Allowed relative difference for numeric comparisons. Curved shapes
            need slack because a faceted mesh cannot match a curve exactly.
        allow_extra_tags: When ``False``, tags you did not list are reported.
    """

    tags: list[TagExpectation] = field(default_factory=list)
    volume: float | None = None
    area: float | None = None
    size: float | None = None
    rel_tol: float = 0.01
    allow_extra_tags: bool = False

    @classmethod
    def build(cls, tags=None, **kwargs) -> "Expectations":
        """Create expectations from a convenient mapping.

        ``tags`` maps a name to its dimension, or to ``(dimension, measure)``:

        >>> Expectations.build({"inlet": 2, "wall": (2, 6.28)}, volume=3.14)
        """
        parsed = []
        for name, spec in (tags or {}).items():
            if isinstance(spec, (tuple, list)):
                parsed.append(TagExpectation(name, int(spec[0]), None if spec[1] is None else float(spec[1])))
            else:
                parsed.append(TagExpectation(name, int(spec)))
        return cls(tags=parsed, **kwargs)

    @property
    def is_empty(self) -> bool:
        """True when the caller stated nothing to compare against."""
        return not self.tags and self.volume is None and self.area is None and self.size is None
