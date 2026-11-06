
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds.latitude.values
lon = ds.longitude.values

# Region bounds
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25

# Check actual lat/lon values in region
lat_in = lat[(lat >= lat_min) & (lat <= lat_max)]
lon_in = lon[(lon >= lon_min) & (lon <= lon_max)]
print("Lat values in region:", lat_in[0], "to", lat_in[-1], "count:", len(lat_in))
print("Lon values in region:", lon_in[0], "to", lon_in[-1], "count:", len(lon_in))

# Check if there are values just outside the bounds
print("Lat just below min:", lat[np.where(lat >= lat_min)[0][0] - 1] if np.where(lat >= lat_min)[0][0] > 0 else "N/A")
print("Lat just above max:", lat[np.where(lat <= lat_max)[0][-1] + 1] if np.where(lat <= lat_max)[0][-1] < len(lat)-1 else "N/A")
print("Lon just below min:", lon[np.where(lon >= lon_min)[0][0] - 1] if np.where(lon >= lon_min)[0][0] > 0 else "N/A")
print("Lon just above max:", lon[np.where(lon <= lon_max)[0][-1] + 1] if np.where(lon <= lon_max)[0][-1] < len(lon)-1 else "N/A")

# Get the actual indices
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
print(f"Lat indices: {lat_idx[0]}..{lat_idx[-1]}, n={len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]}..{lon_idx[-1]}, n={len(lon_idx)}")

# Save the actual lat/lon values for the region
np.save('/tmp/region_lat.npy', lat[lat_idx])
np.save('/tmp/region_lon.npy', lon[lon_idx])
print("Saved region lat/lon")
print("Region lat values:", lat[lat_idx][:5], "...", lat[lat_idx][-5:])
print("Region lon values:", lon[lon_idx][:5], "...", lon[lon_idx][-5:])
