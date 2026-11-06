import xarray as xr, numpy as np, pandas as pd

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

t = pd.to_datetime(ds.time.values)
print("time range:", t.min(), "->", t.max(), " n =", len(t))
# check daily continuity
diffs = np.diff(t.values).astype("timedelta64[D]").astype(int)
print("unique day steps:", np.unique(diffs))

lat = ds.latitude.values; lon = ds.longitude.values
print("lat range:", lat.min(), lat.max(), "step approx:", np.unique(np.round(np.diff(lat),6))[:5])
print("lon range:", lon.min(), lon.max(), "step approx:", np.unique(np.round(np.diff(lon),6))[:5])

lat_in = (lat >= 54.13) & (lat <= 55.33)
lon_in = (lon >= 14.67) & (lon <= 15.87)
print("lat indices:", np.where(lat_in)[0].min(), "->", np.where(lat_in)[0].max(), "count", lat_in.sum())
print("lon indices:", np.where(lon_in)[0].min(), "->", np.where(lon_in)[0].max(), "count", lon_in.sum())
print("lat vals at sel:", lat[lat_in][:3], "...", lat[lat_in][-3:])
print("lon vals at sel:", lon[lon_in][:3], "...", lon[lon_in][-3:])
