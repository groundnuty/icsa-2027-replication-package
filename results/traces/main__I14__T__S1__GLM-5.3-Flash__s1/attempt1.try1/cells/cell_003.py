import fsspec, traceback
fs = fsspec.filesystem('onedata')
try:
    parent = fs.ls('icsa2027_data_20261101T090944Z')
    print("parent entries:", len(parent))
    for p in parent[:50]:
        print(p)
except Exception:
    traceback.print_exc()
