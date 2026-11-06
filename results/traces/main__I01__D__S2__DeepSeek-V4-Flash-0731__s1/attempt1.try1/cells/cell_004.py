
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
# Check lat/lon ranges
print("Lat range:", ds.latitude.min().values, ds.latitude.max().values)
print("Lon range:", ds.longitude.min().values, ds.longitude.max().values)
print("Time range:", ds.time.min().values, ds.time.max().values)
# Check lat/lon grid
print("Lat values around 54.13-55.33:")
lats = ds.latitude.values
lons = ds.longitude.values
print(lats[(lats >= 54.13) & (lats <= 55.33)])
print("Lon values around 14.67-15.87:")
print(lons[(lons >= 14.67) & (lons <= 15.87)])
