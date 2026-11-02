"""Reading and writing mesh files.

:func:`load_mesh` picks a reader from the file extension, and :func:`register_reader`
lets you add new formats without editing this package.

Why not simply use meshio? The research behind this project found it has had no release
since January 2024, with a NumPy 2 write fix still unmerged. Reading the two formats below
needs little code, and it lets this package keep track of what it skips. You can still use
any other reader by passing its arrays to ``Mesh.from_arrays``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from ..mesh import Mesh
from .errors import MeshFormatError
from .msh import parse_msh, write_msh22
from .stl import parse_stl

#: Maps a lower-case file extension to a function that turns file bytes into a Mesh.
READERS: dict[str, Callable[[bytes], Mesh]] = {".msh": parse_msh, ".stl": parse_stl}


def register_reader(extension: str, reader: Callable[[bytes], Mesh]) -> None:
    """Teach :func:`load_mesh` a new format. ``reader`` receives the file's bytes."""
    READERS[extension.lower()] = reader


def parse_mesh(data: bytes, filename: str) -> Mesh:
    """Parse file contents already in memory, as with a web upload."""
    extension = Path(filename).suffix.lower()
    if extension not in READERS:
        known = ", ".join(sorted(READERS))
        raise MeshFormatError(f"Unsupported file type {extension or '(none)'!r}. Supported: {known}")
    mesh = READERS[extension](data)
    mesh.source = Path(filename).name
    return mesh


def load_mesh(path: str | os.PathLike) -> Mesh:
    """Read a mesh file from disk."""
    path = Path(path)
    return parse_mesh(path.read_bytes(), path.name)


__all__ = ["MeshFormatError", "load_mesh", "parse_mesh", "register_reader", "write_msh22", "READERS"]
