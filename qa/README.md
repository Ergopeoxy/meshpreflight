# QA pack

This folder answers one question: **does meshpreflight do what it claims, and how would we know if it stopped?**

It holds sample files, the result expected for each, and tools that compare expected with actual.

## Start here

Install the project, including test tools:

```bash
pip install -e ".[dev]"
```

Run every scenario and write the expected-against-actual tables:

```bash
python qa/run_qa.py
```

Then open [results/qa-report.md](results/qa-report.md). To see one scenario in full:

```bash
python qa/run_qa.py --only TAG-04
```

Sample output:

```text
[pass] Python        status: expected errors | actual errors
[pass] Python        findings: expected ['BOUNDARY_UNTAGGED', 'TAG_EMPTY'] | actual ['BOUNDARY_UNTAGGED', 'TAG_EMPTY']
[pass] Command line  status: expected errors | actual errors
[pass] Command line  exit code: expected 1 | actual 1
[pass] Web           plots returned: expected True | actual True
```

To check one sample yourself and compare by eye:

```bash
meshpreflight check qa/samples/tag_failures/wall_cells_lost.msh --expect inlet:2 --expect outlet:2 --expect wall:2 --expect fluid:3
```

## What's here

| Path | What it is |
|---|---|
| [TEST_PLAN.md](TEST_PLAN.md) | Scope, approach, and every scenario in plain language |
| [samples/](samples/) | 76 test files: valid, damaged, and limits of the tool |
| [scenarios.json](scenarios.json) | Input and expected result for each scenario (generated, so don't edit by hand) |
| [build_scenarios.py](build_scenarios.py) | Readable source of the scenarios, with expected values written as formulas |
| [generate_samples.py](generate_samples.py) | Rebuilds the sample files. Needs Gmsh |
| [run_qa.py](run_qa.py) | Compares expected with actual through Python, command line and web |
| [mutation_check.py](mutation_check.py) | Breaks the code on purpose to prove these tests notice |
| [performance.py](performance.py) | Measures speed as meshes grow |
| [results/](results/) | Latest reports, and the bugs QA found |

Related automated tests are in [`tests/`](../tests/): `test_qa_scenarios.py`, `test_qa_properties.py` and `test_qa_interfaces.py`.

## Why the expected answers can be trusted

A test whose input and answer both come from the code being tested proves very little. So `generate_samples.py` and
`build_scenarios.py` **never import meshpreflight**. Every expected result comes from one of these:

- A formula worked out by hand, such as the volume of a tetrahedron being 1/6.
- A file written by real Gmsh, compared with the formula for the shape it was asked to build.
- A plain text edit to a Gmsh file, where the edit itself defines what should be reported.

## Adding a scenario

1. Add the file to `generate_samples.py`, and run it (or place a file in `samples/`).
2. Add a `scenario(...)` entry to `build_scenarios.py`, and work out the expected values **before** running the tool.
3. Run `python qa/build_scenarios.py`, then `python qa/run_qa.py --only YOUR-ID`.

```python
scenario("TAG-11", "Short title", "tag_failures/my_file.msh",
         "Plain-language explanation of why this matters.",
         area_name="Tag failures",
         input={"tags": {"inlet": [2, None]}, "volume": 12.5, "rel_tol": 0.05},
         status="errors",
         findings=["TAG_MISSING"],
         volume=value(12.5, 0.05, trusted=True))
```

`findings` must list every finding code that should appear, so an unexpected extra one also fails the scenario. If the
tool disagrees with you, check your own working as well: three of the first failures here were mistakes in the scenarios
themselves.
