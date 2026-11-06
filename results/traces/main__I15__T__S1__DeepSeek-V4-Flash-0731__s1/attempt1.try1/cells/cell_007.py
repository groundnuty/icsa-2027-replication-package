import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check the lat and lon ranges
print("Lat range:", float(ds.latitude.min()), float(ds.latitude.max()))
print("Lon range:", float(ds.longitude.min()), float(ds.longitude.max()))
print("Time range:", ds.time.values[0], ds.time.values[-1])
print("Time count:", len(ds.time))

# Check region indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
print("\nLat values near 56.13-57.33:")
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lat_idx = np.where(lat_mask)[0]
print("lat indices:", lat_idx[:5], "...", lat_idx[-5:])
print("lat count:", len(lat_idx))
print("lat values:", lat_vals[lat_idx[0]], lat_vals[lat_idx[-1]])

print("\nLon values near 17.71-18.91:")
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lon_idx = np.where(lon_mask)[0]
print("lon indices:", lon_idx[:5], "...", lon_idx[-5:])
print("lon count:", len(lon_idx))
print("lon values:", lon_vals[lon_idx[0]], lon_vals[lon_idx[-1]])
