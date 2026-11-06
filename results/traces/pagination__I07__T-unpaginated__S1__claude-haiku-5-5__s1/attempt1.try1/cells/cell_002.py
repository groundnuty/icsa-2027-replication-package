import re, collections
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
other=[f for f in files if not re.search(r'sst_\d{8}\.nc$', f)]
print(other[:20], len(other))
dates=sorted(re.search(r'sst_(\d{8})\.nc',f).group(1) for f in files if re.search(r'sst_\d{8}\.nc$', f))
print(dates[0], dates[-1], len(dates))
import xarray
with fs.open(files[0],'rb') as f:
    ds=xarray.open_dataset(f, engine='h5netcdf').load()
print(ds)
