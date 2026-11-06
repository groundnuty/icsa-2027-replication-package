import glob, os, datetime as dt
import numpy as np, xarray as xr, time

files = sorted(glob.glob('/work/data/sst_*.nc'))
print("files:", len(files))
j0, j1, i0, i1 = 329, 389, 550, 610
N = len(files)

sst = np.full((N, 61, 61), np.nan, dtype=np.float64)
times = np.empty(N, dtype='datetime64[ns]')

t0 = time.time()
for k, f in enumerate(files):
    ds = xr.open_dataset(f, engine='h5netcdf')
    times[k] = ds['time'].values[0]
    sst[k] = ds['analysed_sst'].isel(time=0).values[j0:j1+1, i0:i1+1].astype(np.float64)
    ds.close()
print(f"loaded {N} days in {time.time()-t0:.1f}s")
np.save('/work/sst_cube.npy', sst)
np.save('/work/times.npy', times)
print("times check:", times[0], times[-1], "monotonic:", (np.diff(times.astype('int64')) > 0).all())
print("expected first/last:", np.datetime64('1991-12-27'), np.datetime64('2012-08-31'))
print("shape:", sst.shape)
