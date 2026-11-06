
import xarray as xr, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lats = ds.latitude.values
lons = ds.longitude.values

# Region: lat 64.39-65.59, lon 23.41-24.61
lat_mask = (lats >= 64.39) & (lats <= 65.59)
lon_mask = (lons >= 23.41) & (lons <= 24.61)
print("Lat indices:", np.where(lat_mask)[0])
print("Lon indices:", np.where(lon_mask)[0])
lat_sel = lats[lat_mask]
lon_sel = lons[lon_mask]
print("Selected lats:", lat_sel)
print("Selected lons:", lon_sel)
print("Num lats:", len(lat_sel), "Num lons:", len(lon_sel))
