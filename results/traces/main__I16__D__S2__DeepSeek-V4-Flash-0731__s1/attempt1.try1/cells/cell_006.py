
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values

# baseline days: 1992-01-01 to 2002-12-31 plus window 1991-12-27..1991-12-31, 2003-01-01..2003-01-05
b_start = np.where(time >= np.datetime64('1991-12-27'))[0][0]
b_end = np.where(time <= np.datetime64('2003-01-05'))[0][-1]
print("baseline data idx range:", b_start, b_end, "days:", b_end-b_start+1)

# Verify boundaries
print("time[b_start]:", time[b_start])
print("time[b_end]:", time[b_end])
print("time[b_start+5]:", time[b_start+5])
print("time[b_end-5]:", time[b_end-5])
