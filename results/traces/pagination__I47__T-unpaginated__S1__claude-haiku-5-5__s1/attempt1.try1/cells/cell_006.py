import fsspec, xarray as xr, re, collections
fs = fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z/'
ds=xr.open_dataset(fs.open(d+'sst_19820101.nc','rb'),engine='h5netcdf')
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding)
files = fs.ls(d.rstrip('/'), detail=False)
dates=sorted(f.split('_')[-1][:8] for f in files)
print(dates[0],dates[-1], len(set(dates)), len(dates))
