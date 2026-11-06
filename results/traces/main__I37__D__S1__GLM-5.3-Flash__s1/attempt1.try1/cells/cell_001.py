import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
print(len(entries))
for e in entries[:50]:
    print(e['name'], e.get('type'), e.get('size'))
