import fsspec, os, json
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(path, detail=True)
    print(len(entries))
    for e in entries[:20]:
        print(e.get('name'), e.get('size'), e.get('type'))
except Exception as ex:
    print('ERR', type(ex).__name__, ex)
