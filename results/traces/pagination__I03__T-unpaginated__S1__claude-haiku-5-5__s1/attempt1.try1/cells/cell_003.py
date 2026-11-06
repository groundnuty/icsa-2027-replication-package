
import fsspec, xarray as xr, re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names = sorted(f.split('/')[-1] for f in files)
print(len(names), names[0], names[-1])
other=[n for n in names if not re.match(r'sst_\d{8}\.nc$',n)]
print('other:',other[:20])
dates=[re.search(r'(\d{8})',n).group(1) for n in names if re.search(r'(\d{8})',n)]
print(len(dates), len(set(dates)))
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf').load()
print(ds)
