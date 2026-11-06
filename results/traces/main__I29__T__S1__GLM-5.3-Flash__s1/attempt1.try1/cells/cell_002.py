import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(entries))
print(entries[0], entries[-1])
