import fsspec,re,collections
fs = fsspec.filesystem('onedata')
files=fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names))
odd=[n for n in names if not re.fullmatch(r'sst_\d{8}\.nc',n)]
print(len(odd), odd[:20])
ds=sorted(n[4:12] for n in names if re.fullmatch(r'sst_\d{8}\.nc',n))
print(ds[0],ds[-1],len(ds), len(set(ds)))
print(sorted(collections.Counter(d[:4] for d in ds).items()))