# Bugs found by QA

The first full QA run happened **before any library code was changed**: 66 of 88 scenarios passed. This page records what
that run and later QA steps revealed. All listed bugs are fixed unless marked open.

## Bugs in the library

Severity reflects the project's main risk: telling someone a bad mesh is fine.

| # | Severity | Bug | Found by | Fix |
|---|---|---|---|---|
| 1 | **High** | A `.msh` file cut off part way, or holding fewer items than it declared, read as a smaller, normal-looking mesh | BAD-11, 12, 13, 14 | Reader confirms end markers and declared counts |
| 2 | **High** | A mesh with no readable cells (points only, or only hexahedra or second-order elements) could end with no error: points-only reported "no problems found" and the others only a warning | ELM-11, LIM-01, LIM-03 | New `EMPTY_MESH` error |
| 3 | **High** | An STL with a `nan` coordinate was read and given a report, when it should have been refused | BAD-19 | Refused with a clear message |
| 4 | **High** | After a failed upload, the web page kept the previous file's green banner under the error | WEB-09, in a browser | Old results clear when a new check starts |
| 5 | Medium | Volume and area were marked as trusted even though skipped elements weren't counted in them | LIM-02 | Marked untrusted, with the reason |
| 6 | Medium | A name used in two dimensions gave false errors, because lookups took the first match | VAL-10 | Lookups consider the dimension |
| 7 | Medium | A `nan` or `inf` in a `.msh` file failed with an obscure error from a library deep inside | BAD-09, 10 | Clear message from the `Mesh` class |
| 8 | Medium | A mesh with no cells kept the previous mesh's quality chart on the web page | WEB-10, in a browser | The chart is hidden when there are no scores |
| 9 | Medium | An accent saved in Latin-1 made a text file get reported as binary, which blocked reading it | VAL-09 | Falls back to Latin-1, and the format line decides what's binary |
| 10 | Low | A named point (dimension 0) was falsely reported as an empty tag | VAL-12 | Named points are only confirmed by name |
| 11 | Low | An incomplete format line crashed with `IndexError` | BAD-05 | Clear message |
| 12 | Low | A text STL cut off between triangles gave no sign of it | SRF-06 | Reader note |
| 13 | Low | `allow_extra_tags` existed in Python, but not on the command line or web page | GMS-07, VAL-09 | Added to both |
| 14 | Low | `meshpreflight demo --level` had no limit: a negative value crashed, and a large one could exhaust memory | Misuse tests | Limited to 1 to 6 |
| 15 | Low | On the web route, unusual JSON, such as a list instead of an object or a non-numeric level, could cause a server error | Code review while writing misuse tests. Fixed before those tests first ran, so no failure was recorded | Input checked, and a general error message added |
| 16 | Low | Pointing the command line at a folder could end in a traceback | The same | Reported as a normal error |
| 17 | Low | A negative tolerance was accepted | The same | Refused |

Bugs 15 to 17 came from reading the code, so unlike the others, they were never seen failing.

## Mistakes in the QA pack itself

These first looked like failures of the tool, but the tool was right. They are listed because checking your own expectations
is part of QA.

| Scenario | Mistake | Correction |
|---|---|---|
| ELM-03 | Forgot that a tetrahedron using corner 3 twice leaves corner 4 unused | Expect `ORPHAN_POINTS` too |
| TAG-08 | The "floating" triangle's corners were in a straight line, so it was correctly also called degenerate | Used a real triangle |
| GMS-06, TAG-03, TAG-05 | The comparison treated repeated findings as extras | Compare the set of codes |
| Two older unit tests | One expected a garbage file to be called binary, and one assumed level 0 should fail | Updated to the decided behaviour |

## Gaps found in the tests

The [mutation check](mutation-report.md) makes deliberate mistakes in a copy of the code. Its first run caught 44 of 47. The
three survivors weren't bugs in the library, but things the tests wouldn't have noticed if they broke. After adding the scenarios below, the full rerun caught all 47:

| Deliberate mistake that survived | Why | Added |
|---|---|---|
| Point numbers treated as list positions | Every sample listed its points in order | VAL-18 |
| Open surface volume wrongly trusted | Another check also marked it untrusted, by coincidence and for the wrong stated reason | SRF-01 and SRF-02 now check the reason |
| Emptied tags vanishing from the table | Only the separate error was tested | TAG-04 now checks the table |

## Still open

These are known and documented, not fixed. Each has a scenario or note, so any change gets noticed.

| Gap | Effect | Where |
|---|---|---|
| Swapping two tags of equal size isn't detected | Inlet and outlet could be reversed unnoticed | LIM-04 |
| A swap can't be detected at all without expected sizes | The user has to state sizes | TAG-10 |
| Flat meshes are only recognised in planes of constant z | A 2D mesh in another plane reads as an open surface | LIM-05 |
| Self-intersecting surfaces aren't detected | A common defect in real STL files goes unreported | README |
| Only linear lines, triangles and tetrahedra are analysed | Other elements are reported as not checked | LIM-01 to LIM-03 |
| Tested only with files from Gmsh | Other tools may write valid files that this rejects or misreads | Test plan |
| Check time grows slightly faster than cell count | A 1.6 million cell mesh took about a minute | [Performance](performance-report.md) |
| Manual web scenarios ran in one browser only | Other browsers are untested | Below |

## Manual web results

Run in the browser inside the Claude desktop app on Windows 11, using the scripted page steps in [TEST_PLAN.md](../TEST_PLAN.md).
These were driven by script in a real browser page, so anything depending on a person's own eyes, such as how clear a chart
looks, had limited coverage. Scenarios WEB-09 and WEB-10 were rerun after their fixes.

| ID | Result | Observed |
|---|---|---|
| WEB-01 | Pass | `TAG_MISSING`, `BOUNDARY_UNTAGGED`, red banner, 4 plot layers |
| WEB-02 | Pass | All five shapes: green banner, no findings |
| WEB-03 | Pass | Amber banner, `OPEN_SURFACE`, "Not trusted: open surface" |
| WEB-04 | Pass | Sphere and cylinder each list only the defects that fit |
| WEB-05 | Pass | The form refuses level 99 |
| WEB-06 | Pass | `cylinder_level2.msh` returned as an attachment, and it uploads again |
| WEB-07 | Pass | Green banner, `TAG_UNEXPECTED` |
| WEB-08 | Pass | No findings with the box ticked |
| WEB-09 | Pass after fix | Error shown, results hidden |
| WEB-10 | Pass after fix | `EMPTY_MESH`, quality card hidden, and it returns for the next good file |
| WEB-11 | Pass | The name displays as text, no image element is created, and no script ran |
| WEB-12 | Pass | 20 checks listed, results hidden |
| WEB-13 | Pass | Results still present on return |
| WEB-14 | Pass | "Working...", button disabled, old results hidden, finished in about 30 seconds |
| WEB-15 | Pass | 175 of 175, plot drawn |
| WEB-16 | Pass | No sideways scrolling at 375 pixels, and light and dark themes both apply |
