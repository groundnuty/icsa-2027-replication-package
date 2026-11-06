import fsspec, traceback
fs = fsspec.filesystem('onedata')
try:
    s2 = fs.ls('icsa2027_data_20261101T090944Z/s2z')
    print("s2z entries:", len(s2))
    print(s2[:3], s2[-3:])
except Exception:
    traceback.print_exc()
