import fsspec
fs = fsspec.filesystem('onedata')
# List the dataset directory
base = 'icsa2027_data_20261101T090944Z/s1z'
try:
    entries = fs.ls(base, detail=True)
    print(len(entries))
    for e in entries[:50]:
        print(e.get('name'), e.get('size'))
except Exception as ex:
    print('ERR', ex)
