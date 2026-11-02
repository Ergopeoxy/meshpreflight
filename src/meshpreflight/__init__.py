"""meshpreflight: check a finite element mesh before you trust a simulation.

Start here::

    from meshpreflight import preflight

    report = preflight("pipe.msh", {"inlet": 2, "outlet": 2, "wall": 2, "fluid": 3})
    print(report.to_text())

The most useful names are re-exported from this module, so users don't need to learn the
internal layout. ``docs/code-walkthrough.md`` explains each module.
"""

from .checks import CHECK_REGISTRY, Check, CheckContext, register_check
from .core import Preflight, preflight
from .defects import DEFECTS, Defect, apply_defect
from .expectations import Expectations, TagExpectation
from .findings import Finding, Severity
from .io import MeshFormatError, load_mesh, parse_mesh, register_reader, write_msh22
from .measurements import measure
from .mesh import CellBlock, Mesh, MeshError
from .quality import QualityLimits, compute_quality
from .report import Report
from .shapes import SHAPES, Box, Cylinder, ExactValues, Rectangle, ReferenceShape, SphereSurface, TorusSurface, get_shape

__version__ = "0.1.0"

__all__ = [
    "Box", "CHECK_REGISTRY", "CellBlock", "Check", "CheckContext", "Cylinder", "DEFECTS", "Defect",
    "ExactValues", "Expectations", "Finding", "Mesh", "MeshError", "MeshFormatError", "Preflight", "QualityLimits",
    "Rectangle", "ReferenceShape", "Report", "SHAPES", "Severity", "SphereSurface", "TagExpectation",
    "TorusSurface", "apply_defect", "compute_quality", "get_shape", "load_mesh", "measure",
    "parse_mesh", "preflight", "register_check", "register_reader", "write_msh22",
]
