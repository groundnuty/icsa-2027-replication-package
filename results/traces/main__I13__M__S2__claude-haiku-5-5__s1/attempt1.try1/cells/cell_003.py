
import xarray as xr, numpy as np, pandas as pd
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding)
sub=ds.sel(latitude=slice(56.09,57.29), longitude=slice(10.55,11.75))
print(sub.sizes, sub.latitude.values[[0,-1]], sub.longitude.values[[0,-1]])
