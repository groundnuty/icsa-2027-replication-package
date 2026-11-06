
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Check lat/lon ranges
print("Lat range:", ds.latitude.values.min(), ds.latitude.values.max())
print("Lon range:", ds.longitude.values.min(), ds.longitude.values.max())
print("Time range:", ds.time.values.min(), ds.time.values.max())

# Find region indices
lat = ds.latitude.values
lon = ds.longitude.values
print("Lat values near region:", lat[(lat>=56.09)&(lat<=57.29)])
print("Lon values near region:", lon[(lon>=10.55)&(lon<=11.75)])
