import numpy as np, h5py, xarray as xr
PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
# decode time via xarray (handles units/calendar correctly)
dst = xr.open_dataset(PATH, engine="h5netcdf")
times = dst["time"].values.astype("datetime64[ns]").astype("datetime64[D]")
print("time[0], time[-1]:", times[0], times[-1])
i0b = np.searchsorted(times, np.datetime64("1991-12-27"))
i1b = np.searchsorted(times, np.datetime64("2003-01-05"), side="right")
i0t = np.searchsorted(times, np.datetime64("2010-06-01"))
i1t = np.searchsorted(times, np.datetime64("2010-08-31"), side="right")
print("indices:", i0b, i1b, i0t, i1t, "(original: 3647 7675 10378 10470)")
assert (i0b, i1b, i0t, i1t) == (3647, 7675, 10378, 10470)
print("times at edges:", times[i0b], times[i1b-1], times[i0t], times[i1t-1])
dst.close()
