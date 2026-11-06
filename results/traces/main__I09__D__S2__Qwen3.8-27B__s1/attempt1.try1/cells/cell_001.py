import fsspec
fs = fsspec.filesystem('onedata')
print("fs type:", type(fs))
# try to list
try:
    items = fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=False)
    print(items)
except Exception as e:
    print("ls error:", e)
