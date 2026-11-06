# The fault batch (issue 11), the evidence

| file | what |
|---|---|
| `../../tests/faults/H3_HAND_TABLE.md` | the hand-worked H3 table, committed at e4bbd9e before the matrix ran on any code |
| `hand-table-main.txt`, `hand-table-fixed.txt` | the same matrix through main's code and through the fixes |
| `pre-fix-tests-on-main.txt` | the batch's tests at e4bbd9e, on main's code: 59 failed, 8 passed. Some fail only for a function or argument main lacks |
| `rescore-13-runs/` | the 13 finished calibration runs, re-scored. `RUN_TAGS.json`: their host, path and Traefik tags come from the lead's description, written after the runs |
| `astra/` | Codex Astra's two reviews and their model and effort lines. Round 3 stopped on the account's usage limit |
| `suite-final.txt` | the suite's last lines at the final head |

The capture files stay on the volume, in `calibration-11/`, with every pull kept by hash in `pulls/` and listed in `PULLS.jsonl`.
