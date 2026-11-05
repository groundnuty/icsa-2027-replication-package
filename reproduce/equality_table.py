"""Regenerate the knowledge-plane equality table (results/knowledge/README.md) from the two result files.

    python reproduce/equality_table.py results/knowledge > equality_table.md

Standard library only. Prints one row per layout: option list, differences, volatile probes, the two checks,
the shared tool-definition hash (first 16 hex digits) and the run time."""
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
print("| layout | options | differences | volatile probes | answered | refused | tool-definition sha256 | UTC |")
print("|---|---|---|---|---|---|---|---|")
for layout in ("S1", "S2"):
    d = json.loads((root / f"equality_{layout}.json").read_text())
    hashes = set(d["tool_definitions_sha256"].values())
    assert len(hashes) == 1, "tool definitions differ between options"
    print(f"| {d['layout']} | {', '.join(d['options'])} | {len(d['differences'])} | {len(d['volatile_probes_in_control'])} | "
          f"{d['live_probes_succeeded_in_every_option']} | {d['disabled_tools_refused_in_every_option']} | "
          f"`{hashes.pop()[:16]}` | {d.get('utc', '')} |")
