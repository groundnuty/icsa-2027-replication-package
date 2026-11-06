import fsspec, xarray as xr, re, collections
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
pat = collections.Counter(re.sub(r'\d','9',f.split('/')[-1]) for f in files)
print(pat.most_common(10))
others=[f for f in files if not re.match(r'.*sst_\d{8}\.nc$',f)]
print(len(others), others[:20])
