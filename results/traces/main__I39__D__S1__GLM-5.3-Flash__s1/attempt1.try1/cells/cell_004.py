import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=True)
print('n entries:', len(entries))
for e in entries[:10]:
    print(e.get('type'), e.get('name'), e.get('size'))
names = [e['name'].split('/')[-1] for e in entries]
print('first:', names[0] if names else None)
print('last:', names[-1] if names else None)
