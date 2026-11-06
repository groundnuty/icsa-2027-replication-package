import json, os
print("cwd:", os.getcwd())
print("files:", os.listdir("output"))
r = json.load(open("output/report.json"))
print("keys:", sorted(r.keys()))
assert sorted(r.keys()) == ["baseline_analysed", "caveats", "complete", "events", "region", "target_analysed"]
assert sorted(r["region"].keys()) == ["lat_max", "lat_min", "lon_max", "lon_min"]
assert sorted(r["baseline_analysed"].keys()) == ["end", "start"]
assert sorted(r["target_analysed"].keys()) == ["end", "start"]
for ev in r["events"]:
    assert sorted(ev.keys()) == ["end", "onset"]
assert isinstance(r["complete"], bool) and isinstance(r["caveats"], str)
import os
for p in ("output/mhw_mask.nc", "output/report.json"):
    print(p, os.path.getsize(p), "bytes")
print("REPORT:")
print(json.dumps(r, indent=2))
