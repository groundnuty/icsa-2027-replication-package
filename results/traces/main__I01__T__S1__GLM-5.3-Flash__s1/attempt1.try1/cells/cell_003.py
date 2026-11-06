import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z'
listing = fs.ls(base, detail=True)
print('n:', len(listing))
for item in listing:
    print(item.get('name'), item.get('type'), item.get('size'))
