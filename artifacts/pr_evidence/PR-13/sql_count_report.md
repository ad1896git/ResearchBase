# SQL count report

Independent review reproduced the old implementation at 13 SELECTs (small), 53 SELECTs (3 paths / 1
Run), and 231 SELECTs (12 paths / 9 Runs). The old implementation therefore had explicit repository
N+1 behavior. PR-13R measurements are recorded separately in `../PR-13R/sql_scaling_report.md`.
