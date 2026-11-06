import fsspec
fs = fsspec.filesystem('onedata')
# List the dataset directory
path = 'icsa2027_data_20261101T090944Z/s1z'
try:
    listing = fs.ls(path, detail=True)
    print(type(listing))
    for item in listing[:50]:
        print(item.get('name'), item.get('type'), item.get('size'))
    print('count:', len(listing))
except Exception as e:
    print('ERR', type(e).__name__, e)
