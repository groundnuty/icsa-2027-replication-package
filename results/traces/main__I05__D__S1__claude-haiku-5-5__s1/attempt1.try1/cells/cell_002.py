files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
import re, collections
names=[f.split('/')[-1] for f in files]
print(len(names), names[:2], names[-3:])
odd=[n for n in names if not re.fullmatch(r'sst_\d{8}\.nc',n)]
print(len(odd), odd[:20])
ds=sorted(n[4:12] for n in names if re.fullmatch(r'sst_\d{8}\.nc',n))
print(ds[0], ds[-1])
import fsspec, os
os.makedirs('/work',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_20210601.nc','/work/t.nc')
import xarray as xr
x=xr.open_dataset('/work/t.nc',engine='h5netcdf'); print(x)