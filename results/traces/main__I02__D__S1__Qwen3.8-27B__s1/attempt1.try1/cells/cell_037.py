import json
with open('/work/output/report.json') as f:
    r = json.load(f)
print(json.dumps(r, indent=2))
print("keys:", sorted(r.keys()))
import os
print("files:", {p: os.path.getsize(p) for p in ['/work/output/mhw_mask.nc','/work/output/report.json']})
