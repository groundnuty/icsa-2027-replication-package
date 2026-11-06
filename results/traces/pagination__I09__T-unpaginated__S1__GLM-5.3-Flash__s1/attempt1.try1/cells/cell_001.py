import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
entries = fs.ls(base, detail=True)
print('n entries:', len(entries))
names = [e['name'] for e in entries]
for e in entries[:40]:
    print(e.get('type'), e.get('name'), e.get('size'))
if len(names) > 40:
    print('...')
    for e in entries[-5:]:
        print(e.get('type'), e.get('name'), e.get('size'))
