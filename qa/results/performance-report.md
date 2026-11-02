# Performance measurements

Measured once on Windows with Python 3.11.5. Timings depend on the computer, so compare the growth between rows and not the absolute numbers. Rebuild this file with `python qa/performance.py`.

## Checks through the Python API

| Mesh | Cells | Check time (s) | Microseconds per cell |
|---|---:|---:|---:|
| Box, level 3 | 3,840 | 0.09 | 23.7 |
| Box, level 4 | 27,648 | 0.84 | 30.5 |
| Box, level 5 | 208,896 | 7.27 | 34.8 |
| Box, level 6 | 1,622,016 | 66.42 | 40.9 |

## Reading a file

| File | Size (MB) | Cells | Read time (s) |
|---|---:|---:|---:|
| Box, level 3, format 2.2 | 0.1 | 3,840 | 0.01 |
| Box, level 4, format 2.2 | 1.0 | 27,648 | 0.11 |
| Box, level 5, format 2.2 | 8.6 | 208,896 | 1.03 |

## Web demo route, including plots

| Mesh | Cells | Time (s) | Response size (MB) |
|---|---:|---:|---:|
| cylinder, level 2 | 1,536 | 0.67 | 0.1 |
| cylinder, level 4 | 79,872 | 4.57 | 3.8 |
| cylinder, level 5 | 614,400 | 39.79 | 29.3 |
| box, level 2 | 576 | 0.11 | 0.1 |
| box, level 4 | 27,648 | 1.31 | 1.8 |
| box, level 5 | 208,896 | 10.97 | 13.4 |
