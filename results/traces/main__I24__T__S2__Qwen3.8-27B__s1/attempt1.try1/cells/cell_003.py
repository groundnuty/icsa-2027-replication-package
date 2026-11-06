import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

lat = ds.latitude.values  # float32
lon = ds.longitude.values

# look near bounds
for name, arr, lo, hi in [("lat", lat, 57.5, 58.85), ("lon", lon, 10.2, 11.5)]:
    m = (arr >= lo) & (arr <= hi)
    vals = arr[m]
    print(name, "count near:", len(vals), "first few:", vals[:8], "last few:", vals[-8:])
    # check representation of bounds
    print("  bound float64:", lo, hi)

# which indices satisfy inclusive bounds with tiny tolerance
tol = 1e-5
lat_idx = np.where((lat >= 57.57 - tol) & (lat <= 58.77 + tol))[0]
lon_idx = np.where((lon >= 10.25 - tol) & (lon <= 11.45 + tol))[0]
print("lat_idx:", lat_idx[0], lat_idx[-1], "n=", len(lat_idx), "vals:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon_idx:", lon_idx[0], lon_idx[-1], "n=", len(lon_idx), "vals:", lon[lon_idx[0]], lon[lon_idx[-1]])

# check float32 of bounds
print("float32 bounds:", np.float32(57.57), np.float32(58.77), np.float32(10.25), np.float32(11.45))

# test a small data read
sub = ds.analysed_sst.sel(time=slice("2004-06-01","2004-06-03")).isel(latitude=lat_idx[0:3], longitude=lon_idx[0:3])
print(sub.values)
ds.close(); f.close()
