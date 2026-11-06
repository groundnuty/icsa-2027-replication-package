import xarray as xr
import numpy as np
import pandas as pd

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds["latitude"].values
lon = ds["longitude"].values
lat_sel = (lat >= 57.85 - 1e-9) & (lat <= 59.05 + 1e-9)
lon_sel = (lon >= 21.01 - 1e-9) & (lon <= 22.21 + 1e-9)
print("lat sel idx:", np.where(lat_sel)[0][0], np.where(lat_sel)[0][-1], lat_sel.sum())
print("lon sel idx:", np.where(lon_sel)[0][0], np.where(lon_sel)[0][-1], lon_sel.sum())

# Test reading target slice
t = pd.to_datetime(ds["time"].values)
target_mask = (t >= "2013-06-01") & (t <= "2013-08-31")
pool_mask = (t >= "1991-12-27") & (t <= "2003-01-05")
print("target days:", target_mask.sum(), "pool days:", pool_mask.sum())

sub = ds["analysed_sst"].isel(time=np.where(target_mask)[0],
                              latitude=np.where(lat_sel)[0],
                              longitude=np.where(lon_sel)[0]).values
sub = sub.astype(np.float64)
print("target slice shape:", sub.shape)
print("finite per day (min/max):", np.isfinite(sub).all(axis=(1,2)).min(), np.isfinite(sub).all(axis=(1,2)).max())
finite_all = np.isfinite(sub).all(axis=0)
print("sea cells:", finite_all.sum())
print("sample values (K):", np.nanmedian(sub), sub[45, 10, 10], sub[0,0,0])
print("land fraction:", np.isnan(sub).mean())
ds.close()
