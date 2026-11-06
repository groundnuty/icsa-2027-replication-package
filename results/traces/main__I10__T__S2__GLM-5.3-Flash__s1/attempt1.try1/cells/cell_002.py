import fsspec, xarray as xr, numpy as np

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

lat = ds.latitude.values.astype('float64')
lon = ds.longitude.values.astype('float64')
print("lat range", lat.min(), lat.max(), "n", lat.size)
print("lon range", lon.min(), lon.max(), "n", lon.size)
print("lat step unique:", np.unique(np.round(np.diff(lat),6))[:5])
print("lon step unique:", np.unique(np.round(np.diff(lon),6))[:5])

lat_min, lat_max = 55.67, 56.87
lon_min, lon_max = 16.45, 17.65
lat_sel = (lat >= lat_min - 1e-6) & (lat <= lat_max + 1e-6)
lon_sel = (lon >= lon_min - 1e-6) & (lon <= lon_max + 1e-6)
lat_idx = np.where(lat_sel)[0]
lon_idx = np.where(lon_sel)[0]
print("lat_idx", lat_idx.min(), lat_idx.max(), "n", lat_idx.size, lat[lat_idx].min(), lat[lat_idx].max())
print("lon_idx", lon_idx.min(), lon_idx.max(), "n", lon_idx.size, lon[lon_idx].min(), lon[lon_idx].max())

t = ds.time.values
print("time n:", t.size, t[0], t[-1])
# check daily continuity
d = np.diff(t).astype('timedelta64[D]').astype(int)
print("diff days unique:", np.unique(d))
