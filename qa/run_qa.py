"""Run every QA scenario and report expected against actual results.

Each scenario in qa/scenarios.json runs through all three ways of using the tool: the Python
API, the command line and the web route. So a scenario passes only if all three give the expected
answer, which also catches an interface that drifts away from the others.

    python qa/run_qa.py                  Print a summary and write qa/results/
    python qa/run_qa.py --only TAG-04    Run one scenario and show every comparison

The exit code is 1 if anything fails, so CI can use it directly.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy
import scipy

from meshpreflight import MeshFormatError, __version__, preflight
from meshpreflight.cli import main as cli_main
from meshpreflight.web import create_app

QA_DIR = Path(__file__).parent
SAMPLES = QA_DIR / "samples"
RESULTS = QA_DIR / "results"


@dataclass
class Comparison:
    """One line of expected against actual."""

    channel: str
    item: str
    expected: str
    actual: str
    passed: bool


@dataclass
class ScenarioResult:
    """Everything compared for one scenario."""

    id: str
    area: str
    title: str
    file: str
    why: str
    comparisons: list[Comparison] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.comparisons)


def load_scenarios() -> list[dict]:
    return json.loads((QA_DIR / "scenarios.json").read_text(encoding="utf-8"))


def _close(actual, expected, rel) -> bool:
    if actual is None or expected is None:
        return actual is expected
    return abs(actual - expected) <= rel * max(abs(expected), 1e-12)


def compare_report(channel: str, data: dict, expected: dict, exit_code: int | None = None) -> list[Comparison]:
    """Compare a report, in its plain-data form, with the expected result."""
    out = []

    def check(item, want, got, ok=None):
        out.append(Comparison(channel, item, str(want), str(got), want == got if ok is None else bool(ok)))

    check("status", expected["status"], data["status"])
    # The full set must match, so an unexpected extra finding is a failure as well.
    check("findings", sorted(expected["findings"]), sorted({f["code"] for f in data["findings"]}))
    if exit_code is not None:
        check("exit code", 1 if expected["status"] == "errors" else 0, exit_code)

    m = data["measurements"]
    for key in ("domain", "n_points", "n_cells"):
        if key in expected:
            check(key, expected[key], m[key])
    if "extent" in expected:
        want = expected["extent"]
        check("extent", want["value"], m["extent"], _close(m["extent"], want["value"], want["rel"]))
    for key in ("volume", "area"):
        if key not in expected:
            continue
        want, got = expected[key], m[key]
        if "value" in want:
            rel = want.get("rel", 0)
            label = f"{want['value']} (within {rel:g})" if want["value"] is not None else "none"
            check(key, label, got["value"], _close(got["value"], want["value"], rel))
        if "trusted" in want:
            check(f"{key} trusted", want["trusted"], got["trusted"])
        if "reason_contains" in want:
            check(f"{key} reason mentions", want["reason_contains"], got["reason"], want["reason_contains"] in got["reason"])
    for tag in expected.get("tags", []):
        name = f"tag '{tag['name']}' (dimension {tag['dim']})"
        row = next((r for r in m["tags"] if r["name"] == tag["name"] and r["dim"] == tag["dim"]), None)
        if row is None:
            check(name, "present", "absent", False)
            continue
        if tag["cells"] is not None:
            check(f"{name} cells", tag["cells"], row["cells"])
        if tag["measure"] is not None:
            check(f"{name} size", f"{tag['measure']:.6g} (within {tag['rel']:g})", f"{row['measure']:.6g}",
                  _close(row["measure"], tag["measure"], tag["rel"]))
    for check_id in expected.get("skipped", []):
        check(f"{check_id} skipped", True, check_id in data["checks_skipped"])
    if "notes_contain" in expected:
        notes = " ".join(data["notes"])
        check("reader note mentions", expected["notes_contain"], notes, expected["notes_contain"] in notes)
    if "message_contains" in expected:
        text = " ".join(f["message"] for f in data["findings"])
        check("message mentions", expected["message_contains"], text, expected["message_contains"] in text)
    if "skipped_elements" in expected:
        wanted = expected["skipped_elements"]
        text = " ".join(f["message"] for f in data["findings"])
        for name, count in wanted.items():
            label = f"{count} {name}"
            check("skipped elements listed", label, text, label in text)
    return out


def compare_error(channel: str, expected_text: str, message: str | None, code_item: str, code_want, code_got) -> list[Comparison]:
    """A damaged file must produce the expected message and failure code, not a report."""
    got = message if message is not None else "no error: a report was returned"
    return [
        Comparison(channel, "error message", f"contains '{expected_text}'", got, message is not None and expected_text in message),
        Comparison(channel, code_item, str(code_want), str(code_got), code_want == code_got),
    ]


def _kwargs(spec: dict) -> dict:
    """Scenario input as keyword arguments for preflight()."""
    return {
        "expect_tags": {name: tuple(value) for name, value in spec.get("tags", {}).items()},
        "expected_volume": spec.get("volume"),
        "expected_area": spec.get("area"),
        "expected_size": spec.get("size"),
        "rel_tol": spec.get("rel_tol", 0.01),
        "allow_extra_tags": spec.get("allow_extra_tags", False),
    }


def run_api(scenario: dict) -> list[Comparison]:
    expected = scenario["expected"]
    path = SAMPLES / scenario["file"]
    try:
        report = preflight(path, **_kwargs(scenario["input"]))
    except MeshFormatError as error:
        if "error" in expected:
            return compare_error("Python", expected["error"], str(error), "raises", "MeshFormatError", "MeshFormatError")
        return [Comparison("Python", "report", "a report", f"error: {error}", False)]
    if "error" in expected:
        return compare_error("Python", expected["error"], None, "raises", "MeshFormatError", "nothing")
    # JSON round trip: confirms that the report really can be serialised.
    return compare_report("Python", json.loads(report.to_json()), expected)


def _cli_arguments(scenario: dict) -> list[str]:
    spec = scenario["input"]
    arguments = ["check", str(SAMPLES / scenario["file"]), "--json"]
    for name, (dim, size) in spec.get("tags", {}).items():
        arguments += ["--expect", f"{name}:{dim}" + ("" if size is None else f":{size!r}")]
    for key, flag in (("volume", "--volume"), ("area", "--area"), ("size", "--size"), ("rel_tol", "--tolerance")):
        if key in spec:
            arguments += [flag, repr(spec[key])]
    if spec.get("allow_extra_tags"):
        arguments.append("--allow-extra-tags")
    return arguments


def run_cli(scenario: dict) -> list[Comparison]:
    expected = scenario["expected"]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = cli_main(_cli_arguments(scenario))
        except SystemExit as stop:
            code = f"exited: {stop.code}"
    if "error" in expected:
        message = stderr.getvalue() or None
        return compare_error("Command line", expected["error"], message, "exit code", 2, code)
    if code not in (0, 1):
        return [Comparison("Command line", "exit code", "0 or 1", f"{code}: {stderr.getvalue().strip()}", False)]
    return compare_report("Command line", json.loads(stdout.getvalue()), expected, code)


def run_web(scenario: dict, client) -> list[Comparison]:
    expected = scenario["expected"]
    spec = scenario["input"]
    path = SAMPLES / scenario["file"]
    tags = [{"name": name, "dim": dim, "measure": size} for name, (dim, size) in spec.get("tags", {}).items()]
    form = {"file": (io.BytesIO(path.read_bytes()), path.name), "tags": json.dumps(tags)}
    for key in ("volume", "area", "size", "rel_tol"):
        if key in spec:
            form[key] = repr(spec[key])
    if spec.get("allow_extra_tags"):
        form["allow_extra_tags"] = "true"
    response = client.post("/api/analyze", data=form, content_type="multipart/form-data")
    data = response.get_json(silent=True) or {}
    if "error" in expected:
        return compare_error("Web", expected["error"], data.get("error"), "HTTP status", 400, response.status_code)
    if response.status_code != 200:
        return [Comparison("Web", "HTTP status", "200", f"{response.status_code}: {data.get('error')}", False)]
    result = compare_report("Web", data, expected)
    result.append(Comparison("Web", "plots returned", "True", str(bool(data.get("plots"))), bool(data.get("plots"))))
    return result


def run_scenario(scenario: dict, client) -> ScenarioResult:
    result = ScenarioResult(scenario["id"], scenario["area"], scenario["title"], scenario["file"], scenario["why"])
    for name, runner in (("Python", lambda s: run_api(s)), ("Command line", lambda s: run_cli(s)), ("Web", lambda s: run_web(s, client))):
        try:
            result.comparisons.extend(runner(scenario))
        except Exception as error:  # A crash is a test failure to report, not a reason to stop the run.
            result.comparisons.append(Comparison(name, "ran without crashing", "True", f"{type(error).__name__}: {error}", False))
    return result


def run_all(only: str | None = None) -> list[ScenarioResult]:
    client = create_app().test_client()
    return [run_scenario(s, client) for s in load_scenarios() if only is None or s["id"] == only]


def _escape(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_report(results: list[ScenarioResult]) -> None:
    """Write the expected-against-actual tables as Markdown and JSON."""
    passed = sum(r.passed for r in results)
    comparisons = sum(len(r.comparisons) for r in results)
    lines = [
        "# QA results: expected against actual", "",
        f"**{passed} of {len(results)} scenarios passed**, covering {comparisons} individual comparisons.", "",
        f"meshpreflight {__version__}, Python {platform.python_version()}, NumPy {numpy.__version__}, "
        f"SciPy {scipy.__version__}, {platform.system()}.", "",
        "Each scenario ran through the Python API, the command line and the web route, and a scenario "
        "passes only if all three match. Rebuild this file with `python qa/run_qa.py`.", "",
        "## Summary", "",
        "| Area | Passed | Total |", "|---|---:|---:|",
    ]
    areas: dict[str, list[ScenarioResult]] = {}
    for result in results:
        areas.setdefault(result.area, []).append(result)
    for name, group in areas.items():
        lines.append(f"| {name} | {sum(r.passed for r in group)} | {len(group)} |")

    failed = [r for r in results if not r.passed]
    if failed:
        lines += ["", "## Failures", ""]
        for result in failed:
            lines += [f"### {result.id}: {result.title}", "", "| Interface | Item | Expected | Actual |", "|---|---|---|---|"]
            lines += [f"| {c.channel} | {_escape(c.item)} | {_escape(c.expected)} | {_escape(c.actual)} |"
                      for c in result.comparisons if not c.passed]
            lines.append("")

    lines += ["", "## All scenarios", ""]
    for name, group in areas.items():
        lines += [f"### {name}", ""]
        for result in group:
            mark = "PASS" if result.passed else "FAIL"
            lines += [f"#### {result.id} [{mark}]: {result.title}", "", f"File: `{result.file}`. {result.why}", "",
                      "| Item | Expected | Actual (Python) | Result |", "|---|---|---|---|"]
            for comparison in result.comparisons:
                if comparison.channel == "Python":
                    outcome = "pass" if comparison.passed else "**FAIL**"
                    lines.append(f"| {_escape(comparison.item)} | {_escape(comparison.expected)} | {_escape(comparison.actual)} | {outcome} |")
            others = [c for c in result.comparisons if c.channel != "Python"]
            other_pass = sum(c.passed for c in others)
            lines += ["", f"Command line and web: {other_pass} of {len(others)} comparisons passed.", ""]

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "qa-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = [{**asdict(r), "passed": r.passed} for r in results]
    (RESULTS / "qa-results.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run QA scenarios: expected against actual.")
    parser.add_argument("--only", metavar="ID", help="run one scenario and print every comparison")
    parser.add_argument("--no-write", action="store_true", help="don't update qa/results/ (used by mutation_check.py)")
    args = parser.parse_args()

    results = run_all(args.only)
    if args.only:
        if not results:
            print(f"No scenario called {args.only}")
            return 2
        for comparison in results[0].comparisons:
            mark = "pass" if comparison.passed else "FAIL"
            print(f"[{mark}] {comparison.channel:<13} {comparison.item}: expected {comparison.expected} | actual {comparison.actual}")
        return 0 if results[0].passed else 1

    if not args.no_write:
        write_report(results)
    for result in results:
        if not result.passed:
            print(f"FAIL {result.id}: {result.title}")
            for comparison in result.comparisons:
                if not comparison.passed:
                    print(f"     {comparison.channel} / {comparison.item}: expected {comparison.expected} | actual {comparison.actual}")
    passed = sum(r.passed for r in results)
    print(f"\n{passed} of {len(results)} scenarios passed. Tables are in {RESULTS / 'qa-report.md'}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
