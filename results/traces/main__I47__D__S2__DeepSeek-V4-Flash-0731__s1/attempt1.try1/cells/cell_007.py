
import xarray as xr
import numpy as np
import json

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_slice = slice(545, 605)
lon_slice = slice(721, 781)

base = ds.analysed_sst.isel(time=slice(3647, 7675), latitude=lat_slice, longitude=lon_slice).load()
tgt = ds.analysed_sst.isel(time=slice(13665, 13757), latitude=lat_slice, longitude=lon_slice).load()

base_time = base.time.values
tgt_time = tgt.time.values
lat_vals = base.latitude.values
lon_vals = base.longitude.values

print("base time", base_time[0], base_time[-1], "n=", len(base_time))
print("tgt time", tgt_time[0], tgt_time[-1], "n=", len(tgt_time))

# Save for later
np.save('/work/base_data.npy', base.values)
np.save('/work/tgt_data.npy', tgt.values)
np.save('/work/base_time.npy', base_time.astype('datetime64[D]').astype('int64'))
np.save('/work/tgt_time.npy', tgt_time.astype('datetime64[D]').astype('int64'))
np.save('/work/lat_vals.npy', lat_vals)
np.save('/work/lon_vals.npy', lon_vals)
print("saved")
