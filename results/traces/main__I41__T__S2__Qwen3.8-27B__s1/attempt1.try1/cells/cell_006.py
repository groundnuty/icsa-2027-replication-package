import fsspec, xarray as xr, numpy as np, pandas as pd, pickle, os
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")

t = pd.to_datetime(ds.time.values)
target = pd.date_range("2021-06-01","2021-08-31")
ti = (t.index.get_indexer(target, method="exact"))
print("target idx range:", ti.min(), ti.max(), len(ti), np.all(np.diff(ti)==1), np.all(np.isfinite(ti)))

lat0,lat1,lon0,lon1 = 404,463,559,618
sub = ds['analysed_sst'].isel(time=ti, latitude=slice(lat0,lat1+1), longitude=slice(lon0,lon1+1))
sst_t = sub.values.astype(np.float64)  # (92, 60, 60)
print("target shape:", sst_t.shape, sst_t.dtype)
finite = np.isfinite(sst_t).all(axis=0)
print("sea cells (finite all target days):", finite.sum(), "of", finite.size)
nan_per_cell = (~np.isfinite(sst_t)).sum(axis=0)
print("cells with any nan:", (nan_per_cell>0).sum())
print("sample finite map corners:", finite[0,0], finite[-1,-1], finite[30,30])
# save for later
os.makedirs("work", exist_ok=True)
np.savez("work/target.npz", sst=sst_t, lat=ds.latitude.values[lat0:lat1+1], lon=ds.longitude.values[lon0:lon1+1],
         time=ds.time.values[ti].astype("datetime64[ns]"), li=li, lj=lj)
print("saved")
