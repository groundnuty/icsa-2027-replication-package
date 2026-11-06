import fsspec, re, xarray as xr
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names), names[:2], names[-3:])
other=[n for n in names if not re.match(r'sst_\d{8}\.nc$',n)]
print(other[:20])
with fs.open(files[0],'rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf').load()
print(ds)