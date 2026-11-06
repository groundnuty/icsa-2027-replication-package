import fsspec, os
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
print("n entries:", len(entries))
for e in entries[:50]:
    print(e.get('type'), e.get('name'), e.get('size'))
