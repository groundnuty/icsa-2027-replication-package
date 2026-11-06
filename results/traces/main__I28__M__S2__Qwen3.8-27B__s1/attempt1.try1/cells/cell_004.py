import xarray as xr
import numpy as np
import pandas as pd
import pickle, time as pytime

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds["latitude"].values
lon = ds["longitude"].values
lat_sel = (lat >= 57.85 - 1e-9) & (lat <= 59.05 + 1e-9)
lon_sel = (lon >= 21.01 - 1e-9) & (lon <= 22.21 + 1e-9)
li = np.where(lat_sel)[0]; lji = np.where(lon_sel)[0]

t = pd.to_datetime(ds["time"].values)
target_mask = (t >= "2013-06-01") & (t <= "2013-08-31")
pool_mask = (t >= "1991-12-27") & (t <= "2003-01-05")
ti = np.where(target_mask)[0]; pi = np.where(pool_mask)[0]
print("target idx:", ti[0], ti[-1], "pool idx:", pi[0], pi[-1])

t0 = pytime.time()
sst_pool = ds["analysed_sst"].isel(time=pi, latitude=li, longitude=lji).values.astype(np.float64)
sst_target = ds["analysed_sst"].isel(time=ti, latitude=li, longitude=lji).values.astype(np.float64)
ds.close()
print("loaded in", pytime.time()-t0, "s")
print("pool:", sst_pool.shape, "target:", sst_target.shape)

sea = np.isfinite(sst_target).all(axis=0)
print("sea cells:", sea.sum(), "of", sea.size)
# check pool finiteness for sea cells
print("sea cells w/ some NaN in pool:", np.isnan(sst_pool)[:, sea].any(axis=0).sum())
print("sea cells with ALL-NaN pool (any doy check later); pool nan frac:", np.isnan(sst_pool).mean())

with open("/tmp/sst_data.pkl", "wb") as f:
    pickle.dump({"sst_pool": sst_pool, "sst_target": sst_target, "sea": sea,
                 "lat": lat[lat_sel].copy(), "lon": lon[lon_sel].copy(),
                 "time_target": t[target_mask].to_pydatetime(),
                 "time_pool": t[pool_mask].to_pydatetime()}, f)
print("saved")
