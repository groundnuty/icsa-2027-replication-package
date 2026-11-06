import fsspec, re, os, collections, xarray as xr
fs = fsspec.filesystem('onedata')
allf = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names = [p.split('/')[-1] for p in allf]
dates = sorted(re.search(r'(\d{8})', n).group(1) for n in names)
print(dates[0], dates[-1], len(dates))
yrs = collections.Counter(d[:4] for d in dates); print(sorted(yrs.items()))
ds = xr.open_dataset('/work/d/first.nc', engine='h5netcdf')
print(ds.analysed_sst.attrs)
print(ds.attrs['comment'])
print(ds.latitude.values[:3], ds.latitude.values[-1])