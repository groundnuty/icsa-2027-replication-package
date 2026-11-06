import fsspec
fs = fsspec.filesystem('onedata')
base = "icsa2027_data_20261101T090944Z"
for e in fs.ls(base + "/s2z", detail=True):
    print(e)