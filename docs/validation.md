# How correctness is established

A tool that judges meshes has to earn trust. The principle here is that each right answer comes from
somewhere other than the code being tested.

Reproduce everything on this page with:

```bash
python -m pytest
```

```bash
meshpreflight validate
```

## The validation suite

`validation.py` holds one list of cases, used by the tests, the command line and the web interface.

### Exact geometry

Flat-sided shapes must match their formulas to rounding error. The faceted cylinder's cross-section is a regular
polygon, whose area has its own formula, so even this curved shape gets an exact test at each level. Sphere and torus
meshes are compared with the formulas `4 pi r^2`, `4/3 pi r^3`, `4 pi^2 a c` and `2 pi^2 a^2 c`.

### Element quality

Perfect cells must get exact best scores. A regular tetrahedron has radius ratio 1, scaled Jacobian 1 and a smallest
dihedral angle of `arccos(1/3)`, which is about 70.53 degrees. Inverting it must turn its scaled Jacobian to -1.

### Defect detection

13 kinds of defect get planted on every shape they apply to, with three random seeds, and the expected finding must be
reported each time.

### No false alarms

Undamaged shapes at three refinement levels must report no errors or warnings. Together with defect detection, this
tests both directions, since a checker that always complains would otherwise pass.

### Convergence

| Study | Theory | Measured on successive refinements |
|---|---:|---|
| Sphere volume | 2 | 1.996, 1.999, 2.000, 2.000 |
| 2D values (L2) | 2 | 1.896, 1.972, 1.993, 1.998, 2.000 |
| 2D slopes (H1) | 1 | 0.959, 0.989, 0.997, 0.999, 1.000 |
| 3D values (L2) | 2 | 1.414, 1.821, 1.951 |

The pass margin is 0.15 on the finest pair. The 3D study is still approaching 2 because its meshes are small, which is
why its final value is furthest from theory.

### Tag demonstration

The same 2D heat problem is solved with and without the `top` boundary tag. On the level 4 mesh:

| Tags | Error (L2) |
|---|---:|
| All present | 0.00131 |
| `top` lost | 0.278 |

That's 213 times worse, with no error raised by the solver, and meshpreflight reports `TAG_MISSING` and
`BOUNDARY_UNTAGGED`.

## Further tests

**Real Gmsh files (`tests/test_io.py`).** Real Gmsh meshes a cylinder and writes it in formats 2.2 and 4.1. The tests
confirm correct tags and sizes within 3%, no false alarms, and matching results between the two formats. They also
confirm that second-order elements are reported as not checked. These tests run only if Gmsh is installed, as it is in
the CI setup.

**Independent reference (`tests/test_geometry.py`).** Sphere volumes and errors are compared with values from a separate
run of `trimesh` 5.2.0 recorded during the project's research: volume 4.179739 at 5,120 faces, and errors of 12.65%, 0.216%
and 0.00338% at 80, 5,120 and 327,680 faces.

**Testing the tests (`tests/test_validation.py`).** A passing test only means something if it could fail. Selected checks
are switched off to confirm that their defect then goes unnoticed. Another test confirms that every defect actually gets
exercised.

**Bad input (`tests/test_io.py`, `tests/test_web.py`).** Damaged files, unsupported versions, binary files and hostile tag
names must all produce clear messages or inert data.

## QA pack

[`qa/`](../qa/README.md) adds sample files with expected results, property tests, misuse tests, a mutation check and manual web scenarios. The suite on this page tests the tool against mathematics, while the QA pack tests it as a user would, with files.

## What this doesn't establish

- **Real-world detection rates.** Planted defects are simple and isolated. Real meshes fail in messier ways. The next
  useful test would be running this on a public set of messy models, such as Thingi10K, and comparing with its published
  defect rates.
- **Correctness of other meshers' files.** Only Gmsh output was tested.
- **Solver accuracy.** `solver.py` is a test tool for one equation, not a validated simulation package.
- **Quality thresholds.** The formulas are tested, but the limits are this project's screening defaults, with no evidence
  that they suit any particular solver.
- **The formula for each published metric, in every edge case.** Metric tests rely on perfect cells and a few special cases,
  and have not been compared with Verdict's own output.
- **Demand.** Nothing here shows that people need this tool, which only real users can settle.
