# Mutation check

**47 of 47 deliberate mistakes were caught.** Each row is one mistake made in a temporary copy of the code. Rebuild this file with `python qa/mutation_check.py`.

| Deliberate mistake | File | Caught by |
|---|---|---|
| Tetrahedron volume divides by 5, not 6 | `geometry.py` | QA scenarios, validation |
| Triangle area forgets the factor of one half | `geometry.py` | QA scenarios, validation |
| Enclosed volume divides by 3, not 6 | `geometry.py` | QA scenarios, validation |
| Boundary keeps shared faces, not outer ones | `geometry.py` | QA scenarios, validation |
| Edge direction is ignored in winding | `geometry.py` | QA scenarios, validation |
| Empty mesh check never fires | `checks/topology.py` | QA scenarios |
| Duplicate point check never fires | `checks/topology.py` | QA scenarios, validation |
| Duplicate cell check never fires | `checks/topology.py` | QA scenarios, validation |
| Holes are not reported | `checks/topology.py` | QA scenarios, validation |
| Fins are not reported | `checks/topology.py` | QA scenarios |
| Winding faults are not reported | `checks/topology.py` | QA scenarios, validation |
| Two pieces count as fine | `checks/topology.py` | QA scenarios |
| Three tets on a face count as fine | `checks/topology.py` | QA scenarios |
| Inverted test uses the wrong sign | `checks/elements.py` | QA scenarios, validation |
| Mixed 2D orientation is ignored | `checks/elements.py` | QA scenarios, validation |
| Collapsed cells with repeated corners are ignored | `checks/elements.py` | QA scenarios, validation |
| Inside-out surface is ignored | `checks/elements.py` | QA scenarios, validation |
| Thin cell limit is disabled | `checks/elements.py` | QA scenarios |
| Missing tags are not reported | `checks/tags.py` | QA scenarios |
| Tag lookup ignores dimension | `checks/tags.py` | QA scenarios |
| Named points are called empty | `checks/tags.py` | QA scenarios |
| Unlabelled boundary test is inverted | `checks/tags.py` | QA scenarios, validation |
| Floating boundary test is inverted | `checks/tags.py` | QA scenarios, validation |
| Cells with no region are ignored | `checks/tags.py` | QA scenarios |
| Unit mistakes are not recognised | `checks/scale.py` | QA scenarios, validation |
| Tolerance is twice as loose as requested | `checks/scale.py` | QA scenarios |
| Tag sizes are not compared | `checks/scale.py` | QA scenarios, validation |
| Format 2.2 tags are all read as zero | `io/msh.py` | QA scenarios |
| Format 4.1 tags are all read as zero | `io/msh.py` | QA scenarios |
| Cut-off check on cell count is removed | `io/msh.py` | QA scenarios |
| Missing end marker is accepted | `io/msh.py` | QA scenarios |
| Node numbers treated as positions | `io/msh.py` | QA scenarios |
| Physical names are dropped | `io/msh.py` | QA scenarios |
| STL corners are joined too eagerly | `io/stl.py` | QA scenarios |
| STL header word decides binary or text | `io/stl.py` | QA scenarios |
| Open surface volume is trusted | `measurements.py` | QA scenarios |
| Inverted volume is trusted | `measurements.py` | QA scenarios |
| Totals are trusted despite skipped elements | `measurements.py` | QA scenarios |
| Named tags with no cells vanish from the table | `measurements.py` | QA scenarios |
| Status ignores errors | `report.py` | QA scenarios |
| Command line always exits 0 | `cli.py` | QA scenarios |
| Command line ignores the tolerance | `cli.py` | QA scenarios |
| Web interface ignores expected volume | `web/app.py` | QA scenarios |
| Web interface ignores allow_extra_tags | `web/app.py` | QA scenarios |
| Tetrahedron radius ratio is wrong | `quality.py` | validation |
| Scaled Jacobian loses its sign | `quality.py` | validation |
| Smallest angle is the largest angle | `quality.py` | validation |
