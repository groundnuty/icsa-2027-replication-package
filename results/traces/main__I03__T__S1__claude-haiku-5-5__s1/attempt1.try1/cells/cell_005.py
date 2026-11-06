import fsspec, re, collections
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
dates=sorted(re.search(r'(\d{8})',n).group(1) for n in names)
print(dates[0],dates[-1], len(set(dates)))
print(collections.Counter(d[:4] for d in dates))
print(any(d.startswith('1992') or d.startswith('2014') for d in dates))