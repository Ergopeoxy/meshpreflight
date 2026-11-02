"""Run every QA scenario in qa/scenarios.json as a test, through all three interfaces."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("flask")

_PATH = Path(__file__).parent.parent / "qa" / "run_qa.py"
_SPEC = importlib.util.spec_from_file_location("run_qa", _PATH)
run_qa = importlib.util.module_from_spec(_SPEC)
import sys  # noqa: E402

sys.modules["run_qa"] = run_qa  # Dataclasses look their module up here while being defined.
_SPEC.loader.exec_module(run_qa)

SCENARIOS = run_qa.load_scenarios()


@pytest.fixture(scope="module")
def client():
    return run_qa.create_app().test_client()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario(scenario, client):
    result = run_qa.run_scenario(scenario, client)
    failures = [f"{c.channel} / {c.item}: expected {c.expected}, got {c.actual}" for c in result.comparisons if not c.passed]
    assert not failures, "\n".join(failures)


def test_every_scenario_runs_on_every_interface(client):
    """Guards the runner itself: a scenario must not pass by comparing nothing."""
    for scenario in SCENARIOS:
        channels = {c.channel for c in run_qa.run_scenario(scenario, client).comparisons}
        assert channels == {"Python", "Command line", "Web"}, scenario["id"]


def test_every_sample_file_is_used_by_a_scenario():
    used = {s["file"] for s in SCENARIOS}
    samples = {p.relative_to(run_qa.SAMPLES).as_posix() for p in run_qa.SAMPLES.rglob("*") if p.is_file()}
    assert samples == used, f"Unused samples: {samples - used}. Missing samples: {used - samples}."


def test_a_wrong_expectation_makes_the_runner_fail(client):
    """A QA runner that can't fail is worthless, so feed it a wrong answer on purpose."""
    scenario = next(s for s in SCENARIOS if s["id"] == "VAL-01")
    wrong = {**scenario, "expected": {**scenario["expected"], "volume": {"value": 999.0, "rel": 1e-9}}}
    assert not run_qa.run_scenario(wrong, client).passed
    wrong = {**scenario, "expected": {**scenario["expected"], "findings": ["TAG_MISSING"]}}
    assert not run_qa.run_scenario(wrong, client).passed
