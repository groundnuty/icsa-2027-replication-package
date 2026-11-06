import os
print("cwd:", os.getcwd())
for p in ['output/mhw_mask.nc', 'output/report.json', '/work/output/mhw_mask.nc', '/work/output/report.json']:
    print(p, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else '-')
import json
r = json.load(open('output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert set(r["region"].keys()) == {"lat_min","lat_max","lon_min","lon_max"}
assert isinstance(r["complete"], bool) and isinstance(r["caveats"], str)
assert [ (e["onset"], e["end"]) for e in r["events"] ] == [("2019-06-06","2019-06-22"), ("2019-07-20","2019-07-29")]
print("report schema OK")
