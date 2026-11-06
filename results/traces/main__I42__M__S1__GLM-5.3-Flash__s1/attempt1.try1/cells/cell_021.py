import numpy as np, h5py, pickle, time, os
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
thr = np.load("/work/thr_raw.npy")   # (366, 60, 60) float64, raw (day 60 NaN)
clim = np.load("/work/clim_raw.npy")

# --- fill day 60 with mean of days 59 and 61 (per cell) ---
with np.errstate(invalid="ignore"):
    thr[59] = (thr[58] + thr[60]) / 2.0
    clim[59] = (clim[58] + clim[60]) / 2.0
print("day 60 thr sample:", thr[59,0,0], "clim:", clim[59,0,0])

# --- wrap-around centred 31-day moving mean ---
def smooth_circ(a):  # a: (366, ...) -> centred 31-day moving mean, wrapping
    s = np.zeros_like(a)
    for k in range(-15, 16):
        s += np.roll(a, -k, axis=0)
    return s / 31.0

thr_s = smooth_circ(thr)
clim_s = smooth_circ(clim)
print("smoothed shapes:", thr_s.shape, clim_s.shape, "finite:", np.isfinite(thr_s).all())

# --- verify smoothing manually for a sample cell/doy ---
cell = (10, 10)
d = 200  # doy 200 -> index 199
vals = [thr[(199 + k) % 366, cell[0], cell[1]] for k in range(-15, 16)]
print("manual mean doy200:", np.mean(vals), " smoothed:", thr_s[199, cell[0], cell[1]])

# --- load target-period SST (2012-06-01..2012-08-31) ---
def read_pair(args):
    path, i0, i1, j0, j1 = args
    with h5py.File(path, "r") as f:
        return f["analysed_sst"][0, i0:i1, j0:j1]

with open("/work/window_dates.pkl","rb") as f:
    wd = pickle.load(f)
lat_idx, lon_idx = wd["lat_idx"], wd["lon_idx"]
i0, i1 = lat_idx[0], lat_idx[-1]+1
j0, j1 = lon_idx[0], lon_idx[-1]+1

target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
print("target days:", len(target_dates))
files = [f"{base}/sst_{t:%Y%m%d}.nc" for t in target_dates]
t0 = time.time()
with ProcessPoolExecutor(max_workers=16) as ex:
    chunks = list(ex.map(read_pair, [(f, i0, i1, j0, j1) for f in files], chunksize=4))
print("target read time:", round(time.time()-t0,1), "s")
sst_t = np.stack(chunks).astype(np.float64)  # (92, 60, 60)
np.save("/work/sst_target.npy", sst_t)
print("sst_t:", sst_t.shape, "NaN frac:", np.isnan(sst_t).mean())
# verify time coord of each file matches expected date
for f, t in list(zip(files, target_dates))[:3] + list(zip(files, target_dates))[-3:]:
    with h5py.File(f, "r") as fh:
        raw = fh["time"][0]
    dec = raw  # seconds since 1981-01-01
    import datetime as dtm
    dt = dtm.datetime(1981,1,1) + dtm.timedelta(seconds=int(raw))
    assert dt.date() == t, (f, dt, t)
print("time coords verified")
np.save("/work/thr_smooth.npy", thr_s); np.save("/work/clim_smooth.npy", clim_s)
