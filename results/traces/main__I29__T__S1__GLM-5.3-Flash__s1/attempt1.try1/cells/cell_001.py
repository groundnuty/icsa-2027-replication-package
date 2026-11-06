import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(entries))
for e in entries[:20]:
    print(e)
