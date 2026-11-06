import fsspec, os
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(p, detail=False)
    print(len(entries))
    for e in entries[:50]:
        print(e)
except Exception as ex:
    print('ERR', type(ex).__name__, ex)
