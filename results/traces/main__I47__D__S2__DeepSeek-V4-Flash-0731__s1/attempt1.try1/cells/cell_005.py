
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

time = ds.time.values
import numpy as np
# Baseline extended: 1991-12-27 to 2003-01-05
t0 = np.datetime64('1991-12-27')
t1 = np.datetime64('2003-01-05')
idx_base = np.where((time>=t0)&(time<=t1))[0]
print("base idx", idx_base[0], idx_base[-1], time[idx_base[0]], time[idx_base[-1]], len(idx_base))

# Target: 2019-06-01 to 2019-08-31
t0t = np.datetime64('2019-06-01')
t1t = np.datetime64('2019-08-31')
idx_tgt = np.where((time>=t0t)&(time<=t1t))[0]
print("tgt idx", idx_tgt[0], idx_tgt[-1], time[idx_tgt[0]], time[idx_tgt[-1]], len(idx_tgt))
