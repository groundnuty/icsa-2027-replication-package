
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load region slice for baseline and target
lat_slice = slice(545, 605)  # inclusive 604
lon_slice = slice(721, 781)  # inclusive 780

base = ds.analysed_sst.isel(time=slice(3647, 7675), latitude=lat_slice, longitude=lon_slice).load()
print("base shape", base.shape)

tgt = ds.analysed_sst.isel(time=slice(13665, 13757), latitude=lat_slice, longitude=lon_slice).load()
print("tgt shape", tgt.shape)

print("base time first,last", base.time.values[0], base.time.values[-1])
print("tgt time first,last", tgt.time.values[0], tgt.time.values[-1])
print("lat", base.latitude.values)
print("lon", base.longitude.values)
