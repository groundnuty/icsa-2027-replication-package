import re, collections
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
pat = collections.Counter(re.sub(r'\d','9',f.split('/')[-1]) for f in files)
print(pat.most_common(10))
others=[f for f in files if not re.match(r'.*sst_\d{8}\.nc$',f)]
print(len(others), others[:20])
f0=fs.open(files[0],'rb')
ds=xr.open_dataset(f0,engine='h5netcdf')
print(ds)
