"""The command line: ``meshpreflight check``, ``demo``, ``validate``, ``checks``, ``web``.

Each subcommand is one small function. ``main`` only wires them to argument parsing. The
exit code is 1 when errors are found, so ``meshpreflight check`` can stop a CI pipeline or
a batch script before a bad mesh wastes hours of solver time.
"""

from __future__ import annotations

import argparse
import sys

from .checks import CHECK_REGISTRY
from .core import Preflight, preflight
from .defects import DEFECTS, apply_defect
from .io import MeshFormatError
from .shapes import SHAPES, get_shape
from .validation import run_validation, summarize


def _parse_tag(text: str) -> tuple[str, tuple[int, float | None]]:
    """Read ``NAME:DIM`` or ``NAME:DIM:SIZE``, such as ``inlet:2:3.14``."""
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(f"Expected NAME:DIM or NAME:DIM:SIZE, got {text!r}")
    try:
        return parts[0], (int(parts[1]), float(parts[2]) if len(parts) == 3 else None)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"Bad tag {text!r}: {error}") from error


def _command_check(args: argparse.Namespace) -> int:
    report = preflight(
        args.file,
        dict(args.expect or []),
        expected_volume=args.volume,
        expected_area=args.area,
        expected_size=args.size,
        rel_tol=args.tolerance,
    )
    print(report.to_json() if args.json else report.to_text())
    if args.plot:
        from .viz import mesh_figure

        mesh_figure(report.mesh, report).write_html(args.plot)
        print(f"\nPlot saved to {args.plot}")
    return 1 if report.errors else 0


def _command_demo(args: argparse.Namespace) -> int:
    shape = get_shape(args.shape)
    mesh = shape.mesh(args.level)
    for name in args.defect or []:
        mesh = apply_defect(mesh, name, args.seed)
    print(Preflight().run(mesh, shape.expectations(args.level)).to_text())
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    summary = summarize(run_validation())
    for category, totals in summary["categories"].items():
        print(f"{category:<22} {totals['passed']}/{totals['total']} passed")
    failures = [case for case in summary["cases"] if not case["passed"]]
    for case in failures:
        print(f"FAILED {case['name']}: expected {case['expected']}, got {case['actual']}")
    print(f"\nTotal: {summary['passed']}/{summary['total']} passed")
    return 1 if failures else 0


def _command_checks(args: argparse.Namespace) -> int:
    for check in CHECK_REGISTRY:
        print(f"{check.id}\n  {check.title}: {check.description}\n")
    return 0


def _command_web(args: argparse.Namespace) -> int:
    from .web import create_app

    print(f"Open http://{args.host}:{args.port} in your browser. Press Ctrl+C to stop.")
    create_app().run(host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meshpreflight", description="Check a mesh before you trust a simulation.")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check a .msh or .stl file")
    check.add_argument("file")
    check.add_argument("--expect", action="append", type=_parse_tag, metavar="NAME:DIM[:SIZE]",
                       help="a tag that must exist; repeat for each, e.g. --expect inlet:2")
    check.add_argument("--volume", type=float, help="expected total volume")
    check.add_argument("--area", type=float, help="expected total area")
    check.add_argument("--size", type=float, help="expected largest extent, useful for catching unit mistakes")
    check.add_argument("--tolerance", type=float, default=0.01, help="relative tolerance for sizes (default 0.01)")
    check.add_argument("--json", action="store_true", help="print JSON instead of text")
    check.add_argument("--plot", metavar="FILE.html", help="save an interactive 3D view")
    check.set_defaults(run=_command_check)

    demo = commands.add_parser("demo", help="check a built-in shape, optionally damaged")
    demo.add_argument("shape", choices=sorted(SHAPES))
    demo.add_argument("--level", type=int, default=2, help="refinement level (default 2)")
    demo.add_argument("--defect", action="append", choices=sorted(DEFECTS), help="plant a defect; can be repeated")
    demo.add_argument("--seed", type=int, default=0, help="which cells the defect damages")
    demo.set_defaults(run=_command_demo)

    validate = commands.add_parser("validate", help="test this tool against exact answers")
    validate.set_defaults(run=_command_validate)

    listing = commands.add_parser("checks", help="explain every check")
    listing.set_defaults(run=_command_checks)

    web = commands.add_parser("web", help="start the web interface on this computer")
    web.add_argument("--host", default="127.0.0.1", help="address to listen on (default: this computer only)")
    web.add_argument("--port", type=int, default=5000)
    web.set_defaults(run=_command_web)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except (MeshFormatError, FileNotFoundError, ValueError, ImportError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
