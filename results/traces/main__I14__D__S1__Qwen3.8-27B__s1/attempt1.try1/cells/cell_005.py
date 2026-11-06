import fsspec, json
fs = fsspec.filesystem('onedata')
base2 = "icsa2027_data_20261101T090944Z/s2z"
det2 = fs.ls(base2, detail=True)
print(json.dumps(det2, indent=1, default=str))