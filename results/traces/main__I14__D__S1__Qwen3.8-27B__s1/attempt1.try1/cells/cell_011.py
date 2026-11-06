import xarray as xr
import numpy as np
a = xr.open_dataset('/work/data/sst_19830101.nc', engine="h5netcdf")['analysed_sst'].values[0]
b = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
t_idx = int(np.searchsorted(b.time.values, np.datetime64('1983-01-01')))
assert b.time.values[t_idx] == np.datetime64('1983-01-01')
c = b['analysed_sst'].values[t_idx]
d = np.abs(a-c)
print("max abs diff:", np.nanmax(d), " nan agreement:", np.array_equal(np.isnan(a), np.isnan(c)))
print("identical (incl NaN):", np.array_equal(a, c, equal_nan=True))