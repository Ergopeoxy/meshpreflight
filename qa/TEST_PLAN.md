# QA test plan

## Purpose

meshpreflight tells people whether to trust a mesh. A mistaken "no problems found" could lead someone to trust a wrong
simulation, so this plan treats false reassurance as the most serious kind of failure.

## What could go wrong, most serious first

| Risk | Example | Tested by |
|---|---|---|
| **False reassurance:** a bad mesh is reported as fine | A cut-off file reads as a smaller, clean mesh | Tag failures, damaged files, mutation check |
| **A wrong number is trusted** | Volume of a hole-filled surface is shown without a warning | Measurement comparisons, trust flags |
| **False alarm:** a good mesh is reported as bad | A hole in a plate is called a defect | Valid files, real Gmsh files |
| **Interfaces disagree** | The web page and command line give different answers | Every scenario runs through all three |
| **Crash or confusing error** | A damaged file gives a stack trace | Damaged files, misuse tests |
| **Misleading display** | An old result stays on screen after a failure | Manual web scenarios |
| **Security** | A crafted tag name runs a script in the page | Interface tests, manual web scenarios |
| **Slow on large meshes** | Time grows far faster than mesh size | Performance measurements |

## Levels of testing

| Level | Where | What it establishes |
|---|---|---|
| Scenario tests | `qa/run_qa.py`, `tests/test_qa_scenarios.py` | Real files give the expected results through all three interfaces |
| Validation suite | `meshpreflight validate`, `tests/test_validation.py` | Formulas, planted defects and textbook error rates |
| Property tests | `tests/test_qa_properties.py` | Rules that hold for any mesh, such as moving a shape not changing its volume |
| Interface misuse tests | `tests/test_qa_interfaces.py` | Wrong input gets a clear message and never a crash |
| Mutation check | `qa/mutation_check.py` | The tests really do fail when the code is broken |
| Performance measurements | `qa/performance.py` | How time grows with mesh size |
| Manual web scenarios | This page, below | What actually appears on screen |

## How a scenario passes

Each scenario gives a file and what you'd tell the tool about it. It passes only if **all** of these hold through the
Python API, the command line **and** the web route:

- The overall status matches.
- The set of finding codes matches exactly, so a surprise extra finding fails the scenario.
- Every stated measurement matches within its tolerance, including whether it's marked as trusted.
- The exit code (command line) or HTTP status (web) is correct.
- A damaged file gives the expected message, with no report and no crash.

## Scenario catalogue

The expected values and full explanation of each are in [results/qa-report.md](results/qa-report.md).

### Valid files (VAL): must read correctly and raise no alarm

| ID | Scenario | Key expected result |
|---|---|---|
| VAL-01 | Single tetrahedron, format 2.2 | Volume 1/6, area 2.3660 |
| VAL-02 | The same, format 4.1, node numbers 10 to 40 | The same values |
| VAL-03 | 2D unit square with four named sides | Area 1, each side length 1 |
| VAL-04 | The same square at z = 5 | Still recognised as 2D |
| VAL-05 | The same square with Windows line endings | The same values |
| VAL-06 | Two tetrahedra sharing a face | Volume 1/2, 6 outer faces |
| VAL-07 | Two materials with a tagged inner face | Inner tag isn't an error |
| VAL-08 | Tag names with spaces and an accent | Names arrive unchanged |
| VAL-09 | Accent saved in an older encoding | Isn't mistaken for a binary file |
| VAL-10 | One name in two dimensions | Each is found separately |
| VAL-11 | One tag number in two dimensions | Each is found separately |
| VAL-12 | A named single point | Isn't called empty |
| VAL-13 to 15 | Octahedron STL: text, binary, and binary with a misleading header | Volume 4/3, area 6.9282, 6 joined corners |
| VAL-16 | Cube STL | Volume 1000, area 600 |
| VAL-17 | Only line cells | No invented volume, and checks listed as skipped |
| VAL-18 | Points listed out of order | Volume 1/2: follows point numbers, not list positions |

### Real Gmsh files (GMS)

| ID | Scenario | Key expected result |
|---|---|---|
| GMS-01, 02 | Cylinder in both formats | Sizes match formulas within the faceting tolerance |
| GMS-03 | Plate with a round hole | Area 0.8743, and the hole isn't a defect |
| GMS-04 | Two joined blocks of different material | Volumes, interface and outside match exactly |
| GMS-05 | Sphere surface exported as STL | Volume and area match formulas within 2% |
| GMS-06 | Mesh saved with no physical groups | Missing tags, regions and boundary labels reported |
| GMS-07 | Subset of tags, extras allowed | Others not mentioned |
| GMS-08 | Subset of tags, extras not allowed | Others mentioned as information only |

### Tag failures (TAG): a real Gmsh file, then one edit simulating a converter fault

| ID | Scenario | Expected finding |
|---|---|---|
| TAG-01 | Name of the wall removed | `TAG_MISSING`, `TAG_UNNAMED` |
| TAG-02 | Inlet misspelled | `TAG_MISSING`, `TAG_UNEXPECTED` |
| TAG-03 | All names lost | `TAG_MISSING`, `TAG_UNNAMED` |
| TAG-04 | Wall name kept, its cells lost | `TAG_EMPTY`, `BOUNDARY_UNTAGGED` |
| TAG-05 | All boundary cells lost | `TAG_EMPTY`, `BOUNDARY_NOT_TAGGED` |
| TAG-06 | Half of the solid cells without a region | `DOMAIN_UNTAGGED` |
| TAG-07 | Inlet labelled as the wrong dimension | `TAG_WRONG_DIMENSION`, `TAG_UNNAMED` |
| TAG-08 | Boundary triangle attached to nothing | `FLOATING_FACETS` |
| TAG-09 | Inlet and wall swapped, sizes given | `MEASURE_MISMATCH` |
| TAG-10 | The same swap, no sizes given | Nothing: documents why sizes matter |

### Element and connection problems (ELM)

| ID | Scenario | Expected finding |
|---|---|---|
| ELM-01 | Inside-out tetrahedron | `INVERTED_CELLS`, volume -1/6, untrusted |
| ELM-02 | All corners in one plane | `DEGENERATE_CELLS` |
| ELM-03 | One corner used twice | `DEGENERATE_CELLS`, `ORPHAN_POINTS` |
| ELM-04 | Extremely flat tetrahedron | `LOW_QUALITY_CELLS` warning |
| ELM-05 | The same cell listed twice | `DUPLICATE_CELLS` |
| ELM-06 | Crack from a duplicated point | `DUPLICATE_POINTS` warning |
| ELM-07 | Point used by no cell | `ORPHAN_POINTS`, information only |
| ELM-08 | Two separate pieces | `MULTIPLE_COMPONENTS` warning |
| ELM-09 | Face shared by three tetrahedra | `NONMANIFOLD_FACES` |
| ELM-10 | 2D mesh with one triangle flipped | `INVERTED_CELLS` |
| ELM-11 | Points but no cells | `EMPTY_MESH` |

### Surface problems (SRF)

| ID | Scenario | Expected finding |
|---|---|---|
| SRF-01 | Cube with one side missing | `OPEN_SURFACE`, area 500, volume untrusted |
| SRF-02 | Cube with one triangle flipped | `WINDING_INCONSISTENT`, volume untrusted |
| SRF-03 | Cube inside out | `SURFACE_INVERTED`, volume -1000 |
| SRF-04 | Cube with an extra fin | `NONMANIFOLD_EDGES`, `OPEN_SURFACE` |
| SRF-05 | Two separate cubes | `MULTIPLE_COMPONENTS`, volume 2000 |
| SRF-06 | Text STL with no closing line | Reader note |

### Sizes and units (UNT)

| ID | Scenario | Expected finding |
|---|---|---|
| UNT-01 | Millimetres read as metres | `UNIT_SCALE_MISMATCH` naming 1000 |
| UNT-02 | Millimetres read as inches | `UNIT_SCALE_MISMATCH` naming 25.4 |
| UNT-03 | Volume off by a billion | `UNIT_SCALE_MISMATCH` naming 1000 |
| UNT-04 | Too small by 1000 | `UNIT_SCALE_MISMATCH` saying too small |
| UNT-05 | Wrong, but not a unit ratio | `MEASURE_MISMATCH` |
| UNT-06 | 0.993% off with a 1% limit | Nothing |
| UNT-07 | 1.69% off with a 1% limit | `MEASURE_MISMATCH` |
| UNT-08 | 1.69% off with a 2% limit | Nothing |
| UNT-09 | Expected volume of zero | `MEASURE_MISMATCH`, no crash |
| UNT-10 | Asking an STL for a tag | `TAG_MISSING` |

### Known limits (LIM): documents what the tool doesn't do

| ID | Scenario | Expected result |
|---|---|---|
| LIM-01 | Hexahedra only | `UNSUPPORTED_ELEMENTS`, `EMPTY_MESH` |
| LIM-02 | Tetrahedron plus hexahedron | Warning, and volume untrusted |
| LIM-03 | Second-order Gmsh mesh | `UNSUPPORTED_ELEMENTS`, `EMPTY_MESH` |
| LIM-04 | Inlet and outlet swapped, same size | **Not detected.** Known gap |
| LIM-05 | Flat mesh not in the xy plane | **Treated as a surface.** Known gap |

If someone closes one of these gaps, its scenario will fail, which is the prompt to update it.

### Damaged files (BAD): a clear message, never a crash or partial result

BAD-01 to BAD-21 cover empty files, wrong file types, binary and old-format files, incomplete headers, missing sections,
references to points that don't exist, invalid numbers, `nan` and `inf`, files cut off in several ways, wrong corner
counts, and unsupported extensions.

## Property tests

These don't need a known answer, since they check rules that apply to any mesh:

| Rule | Why it matters |
|---|---|
| Moving a mesh changes no size or finding | Catches calculations tied to a position |
| Rotating a mesh changes no size or finding | Catches calculations tied to one axis |
| Scaling by s multiplies length by s, area by s², and volume by s³, even at extreme scales | Catches fixed tolerances that fail on very large or small models |
| Renumbering points changes nothing | Catches reliance on file order |
| Reordering cells changes nothing | The same |
| An even shuffle of a tetrahedron's corners changes nothing | Only orientation should matter |
| A clean shape stays clean as it's refined | Catches false alarms at some resolutions |
| Checks never modify the mesh | A checker must only look |
| Defects leave the original untouched, and repeat exactly | Failures must be reproducible |
| Two defects at once are both found | One finding mustn't hide another |

## Manual web scenarios

Run these in a browser with `meshpreflight web`. The automated tests confirm what the routes *return*, but only a browser
confirms what's *shown*.

| ID | Steps | Expected result |
|---|---|---|
| WEB-01 | Open the page | Pipe demo with a lost wall tag, red banner, 3D view |
| WEB-02 | For each shape, choose "None" and click Run check | Green banner, no findings |
| WEB-03 | Sphere, "remove faces" | Amber banner, `OPEN_SURFACE`, volume marked "Not trusted" |
| WEB-04 | Switch between sphere and cylinder | The defect menu lists only defects that fit each shape |
| WEB-05 | Enter level 99 | The browser refuses it |
| WEB-06 | Click "Download as .msh" | A file named after the shape and level downloads, and can be uploaded again |
| WEB-07 | Upload the file, listing only `inlet` | Green banner, `TAG_UNEXPECTED` as information |
| WEB-08 | Tick "Don't mention tags I didn't list" and rerun | The information line disappears |
| WEB-09 | Check a good file, then upload a damaged one | **The error appears and the old green banner disappears** |
| WEB-10 | Upload a file with points but no cells | `EMPTY_MESH`, and no quality chart left from the previous mesh |
| WEB-11 | Upload a file with a tag called `<img src=x onerror=...>` | The name shows as plain text, and no script runs |
| WEB-12 | Open "What gets checked" | All checks listed, no results below |
| WEB-13 | Return to "Try a demo" | Earlier results are still there |
| WEB-14 | Cylinder at level 5 | "Working..." shows, the button locks, old results clear, and it finishes |
| WEB-15 | Run validation | All pass, with the plot and tag demonstration |
| WEB-16 | Phone width, light and dark themes | Readable, with no sideways scrolling |

## Out of scope for now

- Other meshers and solvers, since real files have only come from Gmsh so far.
- Large public datasets of real models, such as Thingi10K.
- Browsers other than the one in the desktop app.
- Sustained load on the web server, which is meant for one person on their own computer.

These are real gaps, and [results/bugs-found.md](results/bugs-found.md) lists what's still open.
