import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
items = fs.ls(base, detail=True)
print("n items:", len(items))
for it in items[:80]:
    print(it['type'], it['name'], it.get('size'))
