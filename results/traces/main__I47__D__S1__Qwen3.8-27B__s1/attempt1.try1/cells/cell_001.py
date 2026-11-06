import fsspec
fs = fsspec.filesystem('onedata')
import os
base = 'icsa2027_data_20261101T090944Z/s1z'
try:
    items = fs.ls(base)
    print(items[:50])
    print(len(items))
except Exception as e:
    print("ERR", e)
    # try listing root
    for p in ['/', '~']:
        try:
            print(p, fs.ls(p)[:20])
        except Exception as e2:
            print(p, "ERR", e2)
