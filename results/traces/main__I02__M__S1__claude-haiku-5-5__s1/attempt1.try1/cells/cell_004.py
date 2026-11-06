import os,re
import xarray as xr, numpy as np
d='/data/icsa2027_data_20261101T090944Z/s1z'
files=sorted(os.listdir(d)); print(files[0],files[-1],len(files))
print(sorted(set(f[:4] for f in files)))
print(sorted(set(f for f in files if not re.match(r'sst_\d{8}\.nc$',f)))[:20])
ds=xr.open_dataset(d+'/sst_19820101.nc',engine='h5netcdf')
print(ds.analysed_sst.attrs, ds.attrs['comment'])
print(ds.analysed_sst.dtype, ds.latitude.values[[0,-1]], ds.longitude.values[[0,-1]])