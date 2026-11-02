"""Break the code on purpose and confirm that the QA suite notices.

Passing tests only mean something if the tests would fail on broken code. This script copies
the library to a temporary folder, makes one small deliberate mistake (a "mutation"), then runs
the QA scenarios and the validation suite against that copy. A mutation counts as caught if
either fails. One that survives reveals a gap in the tests.

The real source files are never touched. Run it with:

    python qa/mutation_check.py

Results are written to qa/results/mutation-report.md.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

QA_DIR = Path(__file__).parent
SOURCE = QA_DIR.parent / "src" / "meshpreflight"

#: (description, file, original text, broken text). The original must occur exactly once.
MUTATIONS = [
    ("Tetrahedron volume divides by 5, not 6", "geometry.py", '"ij,ij->i", np.cross(b - a, c - a), d - a) / 6.0', '"ij,ij->i", np.cross(b - a, c - a), d - a) / 5.0'),
    ("Triangle area forgets the factor of one half", "geometry.py", "return 0.5 * np.linalg.norm(triangle_normals", "return 1.0 * np.linalg.norm(triangle_normals"),
    ("Enclosed volume divides by 3, not 6", "geometry.py", '.sum() / 6.0)', '.sum() / 3.0)'),
    ("Boundary keeps shared faces, not outer ones", "geometry.py", "return rows[counts[np.asarray(inverse).reshape(-1)] == 1]", "return rows[counts[np.asarray(inverse).reshape(-1)] == 2]"),
    ("Edge direction is ignored in winding", "geometry.py", "np.where(directed[:, 0] < directed[:, 1], 1, -1)", "np.where(directed[:, 0] < directed[:, 1], 0, 0)"),
    ("Empty mesh check never fires", "checks/topology.py", "if ctx.mesh.n_cells:\n            return []", "if True:\n            return []"),
    ("Duplicate point check never fires", "checks/topology.py", "if len(used) < 2:", "if True:"),
    ("Duplicate cell check never fires", "checks/topology.py", "if extras:", "if False:"),
    ("Holes are not reported", "checks/topology.py", "if not len(open_edges):", "if True:"),
    ("Fins are not reported", "checks/topology.py", "bad = edges[counts > 2]", "bad = edges[counts > 99]"),
    ("Winding faults are not reported", "checks/topology.py", "bad = edges[(counts == 2) & (balance != 0)]", "bad = edges[(counts == 99) & (balance != 0)]"),
    ("Two pieces count as fine", "checks/topology.py", "if len(unique) <= 1:", "if len(unique) <= 2:"),
    ("Three tets on a face count as fine", "checks/topology.py", "bad = counts[inverse] > 2", "bad = counts[inverse] > 9"),
    ("Inverted test uses the wrong sign", "checks/elements.py", 'bad = np.flatnonzero(signed < 0)\n            kind = "tetra"', 'bad = np.flatnonzero(signed > 0)\n            kind = "tetra"'),
    ("Mixed 2D orientation is ignored", "checks/elements.py", "if positive == 0 or negative == 0:", "if True:"),
    ("Collapsed cells with repeated corners are ignored", "checks/elements.py", "bad = np.flatnonzero(repeated | tiny)", "bad = np.flatnonzero(tiny & False)"),
    ("Inside-out surface is ignored", "checks/elements.py", "if closed_and_consistent and enclosed_volume(ctx.mesh.points, triangles) < 0:", "if False:"),
    ("Thin cell limit is disabled", "checks/elements.py", "bad = np.flatnonzero(low & real)", "bad = np.flatnonzero(low & False)"),
    ("Missing tags are not reported", "checks/tags.py", '"TAG_MISSING", Severity.ERROR', '"TAG_MISSING", Severity.INFO'),
    ("Tag lookup ignores dimension", "checks/tags.py", "key = mesh.tag_id(tag.name, tag.dim)", "key = mesh.tag_id(tag.name)"),
    ("Named points are called empty", "checks/tags.py", "elif tag.dim == 0:", "elif False:"),
    ("Unlabelled boundary test is inverted", "checks/tags.py", "missing = np.flatnonzero(~np.isin(boundary_ids, tagged_ids))", "missing = np.flatnonzero(np.isin(boundary_ids, tagged_ids))"),
    ("Floating boundary test is inverted", "checks/tags.py", "floating = np.flatnonzero(~np.isin(facet_ids, domain_ids))", "floating = np.flatnonzero(np.isin(facet_ids, domain_ids))"),
    ("Cells with no region are ignored", "checks/tags.py", "untagged = np.flatnonzero(tags == 0)", "untagged = np.flatnonzero(tags == -1)"),
    ("Unit mistakes are not recognised", "checks/scale.py", "if abs(linear / factor - 1.0) < 0.02:", "if abs(linear / factor - 1.0) < 0.0:"),
    ("Tolerance is twice as loose as requested", "checks/scale.py", "if difference <= expect.rel_tol:", "if difference <= 2 * expect.rel_tol:"),
    ("Tag sizes are not compared", "checks/scale.py", "if tag.measure is not None and row is not None and row.cells:", "if False:"),
    ("Format 2.2 tags are all read as zero", "io/msh.py", "tag = values[3] if n_tags else 0", "tag = 0"),
    ("Format 4.1 tags are all read as zero", "io/msh.py", "tag = abs(groups[0]) if groups else 0", "tag = 0"),
    ("Cut-off check on cell count is removed", "io/msh.py", '_declared_count(element_lines[0], len(element_lines) - 1, "cells")', "pass"),
    ("Missing end marker is accepted", "io/msh.py", "if current is not None:\n        # Without this", "if False:\n        # Without this"),
    ("Node numbers treated as positions", "io/msh.py", "blocks[kind] = CellBlock(kind, order[found], np.asarray(self.tags[kind]))", "blocks[kind] = CellBlock(kind, found, np.asarray(self.tags[kind]))"),
    ("Physical names are dropped", "io/msh.py", "names[(int(parts[0]), int(parts[1]))] = parts[2].strip().strip('\"')", "pass"),
    ("STL corners are joined too eagerly", "io/stl.py", "relative_tolerance: float = 1e-9", "relative_tolerance: float = 1e-1"),
    ("STL header word decides binary or text", "io/stl.py", "if len(data) == 84 + 50 * count:", "if len(data) == 84 + 50 * count and not data.startswith(b'solid'):"),
    ("Open surface volume is trusted", "measurements.py", "if (counts == 1).any():", "if False:"),
    ("Inverted volume is trusted", "measurements.py", "if (signed < 0).any():", "if False:"),
    ("Totals are trusted despite skipped elements", "measurements.py", "if mesh.unsupported:", "if False:"),
    ("Named tags with no cells vanish from the table", "measurements.py", "if key not in seen and key[0] in KIND_OF_DIM:", "if False:"),
    ("Status ignores errors", "report.py", 'if self.errors:\n            return "errors"', 'if False:\n            return "errors"'),
    ("Command line always exits 0", "cli.py", "return 1 if report.errors else 0", "return 0"),
    ("Command line ignores the tolerance", "cli.py", "rel_tol=args.tolerance,", "rel_tol=0.01,"),
    ("Web interface ignores expected volume", "web/app.py", 'volume=number("volume"),', "volume=None,"),
    ("Web interface ignores allow_extra_tags", "web/app.py", 'allow_extra_tags=form.get("allow_extra_tags") == "true"', "allow_extra_tags=False"),
    ("Tetrahedron radius ratio is wrong", "quality.py", "return 3.0 * inradius / circumradius", "return 2.0 * inradius / circumradius"),
    ("Scaled Jacobian loses its sign", "quality.py", "np.sqrt(2.0) * determinant, largest", "np.sqrt(2.0) * np.abs(determinant), largest"),
    ("Smallest angle is the largest angle", "quality.py", "return np.min(angles, axis=0)", "return np.max(angles, axis=0)"),
]


def caught_by(environment: dict) -> list[str]:
    """Run the two suites and name those that failed."""
    commands = {
        "QA scenarios": [sys.executable, str(QA_DIR / "run_qa.py"), "--no-write"],
        "validation": [sys.executable, "-m", "meshpreflight", "validate"],
    }
    failed = []
    for name, command in commands.items():
        if subprocess.run(command, env=environment, capture_output=True, timeout=300).returncode != 0:
            failed.append(name)
    return failed


def run_mutation(description: str, relative: str, original: str, broken: str) -> list[str]:
    target = SOURCE / relative
    text = target.read_text(encoding="utf-8")
    if text.count(original) != 1:
        raise SystemExit(f"Out of date: '{description}': found {text.count(original)} matches in {relative}.")
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "meshpreflight"
        shutil.copytree(SOURCE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        (copy / relative).write_text(text.replace(original, broken), encoding="utf-8")
        environment = {**os.environ, "PYTHONPATH": folder, "PYTHONDONTWRITEBYTECODE": "1"}
        return caught_by(environment)


def main() -> int:
    baseline = caught_by({**os.environ})
    if baseline:
        print(f"The unmodified code already fails: {baseline}. Fix that first.")
        return 2

    rows = []
    for description, relative, original, broken in MUTATIONS:
        failed = run_mutation(description, relative, original, broken)
        rows.append((description, relative, failed))
        print(("caught  " if failed else "SURVIVED"), description, f"({', '.join(failed)})" if failed else "", flush=True)

    survived = [row for row in rows if not row[2]]
    lines = ["# Mutation check", "",
             f"**{len(rows) - len(survived)} of {len(rows)} deliberate mistakes were caught.** Each row is one mistake "
             "made in a temporary copy of the code. Rebuild this file with `python qa/mutation_check.py`.", "",
             "| Deliberate mistake | File | Caught by |", "|---|---|---|"]
    lines += [f"| {d} | `{f}` | {', '.join(c) if c else '**NOT CAUGHT**'} |" for d, f, c in rows]
    (QA_DIR / "results").mkdir(exist_ok=True)
    (QA_DIR / "results" / "mutation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(rows) - len(survived)} of {len(rows)} caught.")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
