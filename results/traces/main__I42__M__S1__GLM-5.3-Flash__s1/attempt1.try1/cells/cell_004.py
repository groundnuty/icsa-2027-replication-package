import xarray as xr, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120615.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
print("lat step:", np.unique(np.diff(ds.latitude.values))[:5], "lon step:", np.unique(np.diff(ds.longitude.values))[:5])
i0 = np.searchsorted(lat, 62.20); i1 = np.searchsorted(lat, 63.50)
print("lat idx", i0, i1)
print(lat[i0-2:i1+2])
j0 = np.searchsorted(lon, 18.68); j1 = np.searchsorted(lon, 19.98)
print("lon idx", j0, j1)
print(lon[j0-2:j1+2])
