import fsspec, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(base, detail=False)
    print(entries[:50])
    print("count:", len(entries))
except Exception as e:
    print("ERR", type(e).__name__, e)
