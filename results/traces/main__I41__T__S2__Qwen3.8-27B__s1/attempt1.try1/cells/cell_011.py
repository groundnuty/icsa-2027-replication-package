import fsspec, xarray as xr, numpy as np, pandas as pd, time
t0=time.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
t = pd.DatetimeIndex(ds.time.values)
span = pd.date_range("1991-12-27","2003-01-05")
ti = t.get_indexer(span)
print("span idx", ti.min(), ti.max(), len(ti), bool((ti>=0).all()))
z = np.load("work/target.npz")
li, lj = z["li"], z["lj"]
lat0,lat1,lon0,lon1 = li[0],li[-1],lj[0],lj[-1]
sub = ds['analysed_sst'].isel(time=ti, latitude=slice(lat0,lat1+1), longitude=slice(lon0,lon1+1))
arr = sub.values.astype(np.float64)
print("shape", arr.shape, "in", round(time.time()-t0,1), "s")
np.savez("work/baseline.npz", sst=arr, time=ds.time.values[ti].astype("datetime64[ns]"))
print("saved; finite frac", float(np.isfinite(arr).mean()))
