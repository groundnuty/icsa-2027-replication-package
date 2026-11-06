
import fsspec, xarray as xr, re, collections
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
other=[f for f in files if not re.search(r'sst_\d{8}\.nc$', f)]
print(len(files), other[:20])
dates=sorted(re.search(r'sst_(\d{8})',f).group(1) for f in files if re.search(r'sst_\d{8}\.nc$', f))
print(dates[0], dates[-1], len(dates))
with fs.open(f'icsa2027_data_20261101T090944Z/s1z/sst_{dates[0]}.nc','rb') as f:
    ds=xr.open_dataset(f, engine='h5netcdf').load()
print(ds)
