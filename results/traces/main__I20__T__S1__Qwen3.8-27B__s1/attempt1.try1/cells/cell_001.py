import fsspec
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z"
try:
    entries = fs.ls(path, detail=True)
except Exception as e:
    print("ls err", e)
    entries = []
for e in entries:
    print(e)
print("count:", len(entries))