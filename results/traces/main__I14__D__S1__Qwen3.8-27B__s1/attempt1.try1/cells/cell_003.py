import fsspec
fs = fsspec.filesystem('onedata')
base = "icsa2027_data_20261101T090944Z/s1z"
# raw detail of a couple entries
det = fs.ls(base, detail=True)
print("count:", len(det))
import json
print(json.dumps(det[:2], indent=1, default=str)[:800])
# list parent
parent = "icsa2027_data_20261101T090944Z"
print("parent entries:")
for f in fs.ls(parent, detail=True):
    print(f)