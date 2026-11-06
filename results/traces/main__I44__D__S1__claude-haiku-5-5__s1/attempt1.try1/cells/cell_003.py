import fsspec, re, collections
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names))
print(sorted(set(n.split('_')[0] for n in names)))
yrs=collections.Counter(n[4:8] for n in names if n.startswith('sst_'))
print(sorted(yrs.items()))
print([n for n in names if not re.match(r'sst_\d{8}\.nc$',n)][:20])