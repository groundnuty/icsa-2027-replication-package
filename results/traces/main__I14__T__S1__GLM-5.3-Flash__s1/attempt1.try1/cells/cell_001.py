import fsspec, traceback
try:
    fs = fsspec.filesystem('onedata')
    base = 'icsa2027_data_20261101T090944Z/s1z'
    entries = fs.ls(base)
    print("n_entries:", len(entries))
    for e in entries[:30]:
        print(e)
except Exception as ex:
    traceback.print_exc()
