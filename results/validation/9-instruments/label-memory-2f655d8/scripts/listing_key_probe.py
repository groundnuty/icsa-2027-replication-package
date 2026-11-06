"""Read-only: on a real T S1 run, what key does the labeller give the S1 listing, against Production.dir_sizes's key?
Does the real gate log's listing and content agree with the real index's ids?"""
import json, sys
from pathlib import Path
from icsa.instruments.fullindex import load_full_index
from icsa.instruments.labeller import label_run
from icsa.extent import CellBox, Extent, PartedExtent
from icsa import grid
run = Path(sys.argv[1])
idx = load_full_index()
box = CellBox(32, 92, 284, 344)
req = PartedExtent(Extent.full(box, [grid.day_index(__import__('datetime').date(2008,6,1))]), Extent.full(box, [grid.day_index(__import__('datetime').date(2008,6,2))]))
out = run / "output" if (run / "output").is_dir() else run
lab = label_run("T", run / "trace", out, idx, req, platform_dir=run, dir_sizes={"s1z": grid.NDAYS})
print("listing keys:", {k: {x: v.to_json()[x] for x in ("path","requests","entries_listed","complete","truncated","dir_size")} for k, v in (lab.listing or {}).items()})
cc = lab.analysis.flags["cross_check"]
print("cross_check:", {k: cc[k] for k in ("source","listing","unknown_file_ids","listing_disagrees","decoded_not_delivered","delivered_not_decoded")})
print("observed:", lab.observed); print("unidentified:", lab.analysis.flags.get("unidentified_source"), "ledger:", lab.analysis.flags.get("ledger"))
print("read files:", None if lab.read is None else lab.read.files)
