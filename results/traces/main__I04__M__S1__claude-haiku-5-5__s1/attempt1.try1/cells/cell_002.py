import os, xarray as xr, numpy as np
D="/data/icsa2027_data_20261101T090944Z/s1z"
fs=sorted(os.listdir(D)); print(fs[0], fs[-1]); print(len(set(f[:4] for f in fs)))
print([f for f in fs if not f.startswith('sst_') or not f.endswith('.nc')][:10])
ds=xr.open_dataset(f"{D}/sst_20200615.nc", engine="h5netcdf"); print(ds)
print(ds.attrs)