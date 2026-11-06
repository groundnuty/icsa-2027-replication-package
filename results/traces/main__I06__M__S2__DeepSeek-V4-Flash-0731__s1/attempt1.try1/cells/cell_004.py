
import xarray as xr
import numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

# Check some time values
print(ds.time.values[:5])
print(ds.time.values[-5:])

# Check the data values range for a small slice
sst = ds.analysed_sst
print("Data type:", sst.dtype)

# Check target period index
t = ds.time.values
t_str = np.datetime_as_string(t, unit='D')
print(t_str[:3], t_str[-3:])
