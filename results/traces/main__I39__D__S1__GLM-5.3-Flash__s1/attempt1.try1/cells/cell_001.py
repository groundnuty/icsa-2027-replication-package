import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(root, detail=True)
    for e in entries[:50]:
        print(e.get('type'), e.get('name'), e.get('size'))
    print('count:', len(entries))
except Exception as ex:
    print('ERR', type(ex).__name__, ex)
