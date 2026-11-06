import fsspec
fs = fsspec.filesystem('onedata')
try:
    listing = fs.ls('icsa2027_data_20261101T090944Z/s1z')
except Exception as e:
    print('err with plain path:', e)
    listing = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print(len(listing))
for p in listing[:50]:
    print(p)
