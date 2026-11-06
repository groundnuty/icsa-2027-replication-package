import fsspec
fs = fsspec.filesystem('onedata')
items = fs.ls('icsa2027_data_20261101T090944Z/s1z')
for it in items:
    print(it)
print("count:", len(items))
