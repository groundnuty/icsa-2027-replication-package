import datetime as dt, os, glob
import xarray as xr, numpy as np

# 1) Sort file list, open all, verify time values are contiguous & correct
files = sorted(glob.glob('/work/data/sst_*.nc'))
print("files:", len(files))
j0, j1, i0, i1 = 329, 389, 329+62-1, 550  # placeholder fix below
j0, j1 = 329, 389
i0, i1 = 550, 610

# verify all times
times = []
with xr.open_mfdataset(files[:5], combine='nested', concat_dim='time') as ds:
    pass

# quick time check without loading data: read time var from each via h5py for speed
import h5py
def read_time_h5(path):
    with h5py.File(path, 'r') as f:
        # time variable
        if 'time' in f:
            vals = f['time'][:]
            return vals[0]
        raise KeyError('time')

tvals = []
bad = []
for f in files:
    try:
        v = read_time_h5(f)
        tvals.append(v)
    except Exception as e:
        bad.append((os.path.basename(f), str(e)[:80]))
print("time-read failures:", len(bad), bad[:5])
print("sample times:", tvals[:2], tvals[-1])
