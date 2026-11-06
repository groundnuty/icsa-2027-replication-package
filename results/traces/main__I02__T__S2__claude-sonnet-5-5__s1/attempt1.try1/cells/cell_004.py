
import fsspec,xarray as xr,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata')
f=fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc","rb")
ds=xr.open_dataset(f,engine="h5netcdf")
sub=ds.analysed_sst.sel(latitude=slice(54.17-1e-4,55.37+1e-4),longitude=slice(13.25-1e-4,14.45+1e-4))
b=sub.sel(time=slice("1991-12-27","2003-01-05")).load()
t=sub.sel(time=slice("2004-06-01","2004-08-31")).load()
print(b.shape,t.shape,b.latitude.values[[0,-1]],b.longitude.values[[0,-1]])
print(np.isnan(b.values).mean(), np.nanmean(t.values), len(pd.DatetimeIndex(b.time.values).unique()))
b.to_netcdf("/tmp/b.nc");t.to_netcdf("/tmp/t.nc")
