import xarray as xr,numpy as np,pandas as pd
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds=xr.open_dataset(p,engine="h5netcdf")
sub=ds.analysed_sst.sel(latitude=slice(54.39-1e-4,55.59+1e-4),longitude=slice(18.25-1e-4,19.45+1e-4))
print(sub.shape, sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]], ds.analysed_sst.attrs)
b=sub.sel(time=slice("1991-12-27","2003-01-05")).load()
t=sub.sel(time=slice("2021-06-01","2021-08-31")).load()
print(b.shape,t.shape,float(t.max()),np.isnan(b.values).mean())
print(pd.Series(b.time.values).diff().value_counts().head(3))
b.to_netcdf("/tmp/b.nc");t.to_netcdf("/tmp/t.nc")