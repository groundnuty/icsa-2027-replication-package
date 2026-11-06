import re, os
allf = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(allf))
names = [p.split('/')[-1] for p in allf]
print(sorted(set(n[:4] for n in names)))
print([n for n in names if not re.match(r'sst_\d{8}\.nc$', n)][:20])
os.makedirs('/work/d', exist_ok=True)
fs.get(allf[0], '/work/d/first.nc')
import xarray as xr
ds = xr.open_dataset('/work/d/first.nc', engine='h5netcdf')
print(ds)