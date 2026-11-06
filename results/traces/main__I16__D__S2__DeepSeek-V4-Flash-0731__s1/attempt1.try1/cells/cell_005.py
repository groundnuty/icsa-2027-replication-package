
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

time = ds.time.values
print("time range:", time[0], time[-1])
print("total days:", len(time))

# Let's identify the relevant time indices
# Baseline 1992-2002
base_start = np.where(time >= np.datetime64('1991-12-27'))[0][0]
base_end = np.where(time <= np.datetime64('2003-01-05'))[0][-1]
print("baseline incl. window days idx:", base_start, base_end, "days:", base_end-base_start+1)

# Target
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]
print("target idx:", t_start, t_end, "days:", t_end-t_start+1)

# Check spacing of time
print("time[:5]:", time[:5])
print("time[-5:]:", time[-5:])
