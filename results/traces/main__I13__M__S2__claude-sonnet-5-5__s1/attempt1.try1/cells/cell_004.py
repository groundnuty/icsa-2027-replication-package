import xarray as xr, numpy as np, pandas as pd
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
s=d.analysed_sst.sel(latitude=slice(56.09-1e-3,57.29+1e-3),longitude=slice(10.55-1e-3,11.75+1e-3))
print(s.shape, s.latitude.values[[0,-1]], s.longitude.values[[0,-1]])
b=s.sel(time=slice("1991-12-27","2003-01-05")).load()
t=s.sel(time=slice("2021-06-01","2021-08-31")).load()
print(b.shape,t.shape, pd.Series(b.time.values).diff().value_counts().head(), float(t.mean()), b.time.values[[0,-1]])
b.to_netcdf("/tmp/b.nc");t.to_netcdf("/tmp/t.nc")