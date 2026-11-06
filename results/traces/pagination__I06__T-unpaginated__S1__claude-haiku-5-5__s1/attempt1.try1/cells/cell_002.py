files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
import re
names=[f.split('/')[-1] for f in files]
print(names[:2], names[-2:])
odd=[n for n in names if not re.fullmatch(r'sst_\d{8}\.nc',n)]
print(len(odd), odd[:20])
import xarray
f=fs.open(files[0],'rb')
ds=xarray.open_dataset(f,engine='h5netcdf')
print(ds)