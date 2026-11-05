"""Keep only the coding labels that belong to THIS cut (lane-snap, #34).

    python filter_labels.py SCORED_ROWS.jsonl LABELS.jsonl OUT.jsonl      prints `labels kept=K dropped_not_in_cut=D` (counts only)

The coders code every finished run whenever it finishes, whatever its start time, but a snapshot's analysis covers the runs started by its cut, and `analysis.inspection.apply` REFUSES a label for a
run that is not among the scored rows ("an inspection label for no scored run"), which would fail the whole analysis. A label for a run outside the cut cannot apply to it, so it is left out, and the count
is reported (a count that is not zero is expected whenever the coders are ahead of the cut; a count equal to all labels would mean a key mismatch, so the report shows it). Nothing else is changed:
a label that is in the cut goes through untouched and every other refusal of `apply` stays in force.
"""
import json
import os
import sys

scored = set()
with open(sys.argv[1]) as fh:
    for line in fh:
        if line.strip():
            r = json.loads(line)
            run = r["run"]
            scored.add((r["block"], f"{run['instance_id']}__{run['option']}__{run['layout']}__{run['model']}__s{run['seed']}"))
kept = dropped = 0
tmp = sys.argv[3] + ".tmp"
with open(sys.argv[2]) as fh, open(tmp, "w") as out:
    for line in fh:
        if not line.strip():
            continue
        e = json.loads(line)
        if (e.get("block"), e.get("run_key")) in scored:
            out.write(line if line.endswith("\n") else line + "\n")
            kept += 1
        else:
            dropped += 1
os.replace(tmp, sys.argv[3])
print(f"labels kept={kept} dropped_not_in_cut={dropped}")
