import fsspec, re, collections
fs = fsspec.filesystem('onedata')
allf = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in allf]
print(len(names))
print([n for n in names if not re.match(r'sst_\d{8}\.nc$',n)][:20])
ds=sorted(n[4:12] for n in names if re.match(r'sst_\d{8}\.nc$',n))
print(ds[0],ds[-1],len(ds))
print(collections.Counter(d[:4] for d in ds))