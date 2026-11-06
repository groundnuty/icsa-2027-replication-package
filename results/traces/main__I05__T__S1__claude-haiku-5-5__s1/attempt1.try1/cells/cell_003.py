import fsspec, re, collections, xarray as xr
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names), collections.Counter(n.split('_')[0] for n in names))
print([n for n in names if not re.match(r'sst_\d{8}\.nc$',n)][:20])
print(names[:2], names[-3:])
f=fs.open(files[0],'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
print(ds)
