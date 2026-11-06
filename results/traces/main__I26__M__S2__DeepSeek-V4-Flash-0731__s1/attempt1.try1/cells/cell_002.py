
import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Check time range
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat range:", ds.latitude.values[0], "to", ds.latitude.values[-1])
print("Lon range:", ds.longitude.values[0], "to", ds.longitude.values[-1])

# Check latitude/longitude values around our region
lat = ds.latitude.values
lon = ds.longitude.values
print("\nLatitudes near 57.83-59.03:")
print(lat[(lat >= 57.83) & (lat <= 59.03)])
print("\nLongitudes near 17.41-18.61:")
print(lon[(lon >= 17.41) & (lon <= 18.61)])

# Check a small sample
print("\nSample SST at [0, 0, 0]:", ds.analysed_sst.values[0, 0, 0])
print("Sample SST at [1000, 300, 500]:", ds.analysed_sst.values[1000, 300, 500])
