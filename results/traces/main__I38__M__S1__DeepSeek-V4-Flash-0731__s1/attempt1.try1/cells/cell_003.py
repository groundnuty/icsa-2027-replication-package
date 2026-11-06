
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20030601.nc', engine='h5netcdf')

# Find indices in the region
lats = ds.latitude.values
lons = ds.longitude.values
print("Lat range:", lats[0], lats[-1], "n:", len(lats))
print("Lon range:", lons[0], lons[-1], "n:", len(lons))

# Region: lat 60.49 to 61.69, lon 17.25 to 18.45
lat_mask = (lats >= 60.49) & (lats <= 61.69)
lon_mask = (lons >= 17.25) & (lons <= 18.45)
print("Lat indices:", np.where(lat_mask)[0])
print("Lon indices:", np.where(lon_mask)[0])

# Check the data variable values
sst = ds.analysed_sst.values[0]
print("SST sample:", sst[lat_mask][:, lon_mask][:3,:3])
print("SST min/max:", np.nanmin(sst), np.nanmax(sst))
print("SST dtype:", sst.dtype)
