
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check the region
# lat 54.17 to 55.37, lon 13.25 to 14.45
lat_mask = (ds.latitude >= 54.17) & (ds.latitude <= 55.37)
lon_mask = (ds.longitude >= 13.25) & (ds.longitude <= 14.45)
print("Lat indices:", ds.latitude.values[lat_mask.values])
print("Lon indices:", ds.longitude.values[lon_mask.values])

# Get region subset dimensions
nlat = lat_mask.sum().item()
nlon = lon_mask.sum().item()
print(f"nlat: {nlat}, nlon: {nlon}")

# Check time range
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Total time points:", len(ds.time))
