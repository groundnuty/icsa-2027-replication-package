import numpy as np, h5py, pickle
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
with h5py.File(f"{base}/sst_19920615.nc","r") as f:
    lat = f["latitude"][:]; lon = f["longitude"][:]
lat_idx = np.where((lat >= 62.25-1e-6) & (lat <= 63.45+1e-6))[0]
lon_idx = np.where((lon >= 18.73-1e-6) & (lon <= 19.93+1e-6))[0]
i0r, i1r = lat_idx[0], lat_idx[-1]+1   # 438..498
j0r, j1r = lon_idx[0], lon_idx[-1]+1   # 487..547

# Correct region indices
print("correct region slices: lat", i0r, i1r, "lon", j0r, j1r, "-> shape", (i1r-i0r, j1r-j0r))

# Re-read both baseline and target with correct indices
from concurrent.futures import ProcessPoolExecutor
def read_pair(args):
    path, i0, i1, j0, j1 = args
    with h5py.File(path, "r") as f:
        return f["analysed_sst"][0, i0:i1, j0:j1]

# baseline: 1991-12-27 .. 2003-01-05
dates = []
d = date(1991,12,27)
while d <= date(2003,1,5):
    dates.append(d); d += timedelta(days=1)
files = [f"{base}/sst_{t:%Y%m%d}.nc" for t in dates]
t0 = __import__("time").time()
with ProcessPoolExecutor(max_workers=16) as ex:
    chunks = list(ex.map(read_pair, [(f, i0r, i1r, j0r, j1r) for f in files], chunksize=8))
print("baseline re-read:", round(__import__("time").time()-t0,1), "s")
arr_corr = np.stack(chunks)
np.save("/work/baseline_region_corr.npy", arr_corr)
print("baseline corr:", arr_corr.shape, "NaN frac:", np.isnan(arr_corr).mean())

# target: 2012-06-01..2012-08-31
tdates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    tdates.append(d); d += timedelta(days=1)
tfiles = [f"{base}/sst_{t:%Y%m%d}.nc" for t in tdates]
t0 = __import__("time").time()
with ProcessPoolExecutor(max_workers=16) as ex:
    tchunks = list(ex.map(read_pair, [(f, i0r, i1r, j0r, j1r) for f in tfiles], chunksize=4))
print("target re-read:", round(__import__("time").time()-t0,1), "s")
sst_t_corr = np.stack(tchunks)
np.save("/work/sst_target_corr.npy", sst_t_corr)
print("target corr:", sst_t_corr.shape, "NaN frac:", np.isnan(sst_t_corr).mean())
