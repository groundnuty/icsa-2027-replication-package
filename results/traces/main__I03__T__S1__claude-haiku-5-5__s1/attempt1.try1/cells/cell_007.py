import fsspec, re, collections
fs = fsspec.filesystem('onedata')
f2 = fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=False)
print(len(f2), f2[:3], f2[-3:])
ns=[f.split('/')[-1] for f in f2]
ds2=sorted(re.findall(r'\d{8}',n)[0] for n in ns if re.findall(r'\d{8}',n))
print(ds2[:1], ds2[-1:], len(ds2), collections.Counter(d[:4] for d in ds2))