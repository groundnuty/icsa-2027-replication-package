import xarray as xr,numpy as np,pandas as pd
fs=sorted(os.listdir(d));print(fs[0],fs[-1])
ds=xr.open_dataset(d+'/sst_20100601.nc',engine='h5netcdf');print(ds)