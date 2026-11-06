import numpy as np, datetime as dt, os, time, json

t_start = time.time()
OUT = "/work/mhw"
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"

# ---------- load ----------
batches = [(0,500),(500,1000),(1000,1500),(1500,2000),(2000,2500),(2500,3300),(3300,4028)]
base = np.concatenate([np.load(f"{OUT}/base_{a:04d}_{b:04d}.npy") for a,b in batches], axis=0)
tgt  = np.load(f"{OUT}/tgt_0000_0092.npy")
print("base:", base.shape, base.dtype, " tgt:", tgt.shape, tgt.dtype)

base_dates = [dt.date(1991,12,27) + dt.timedelta(days=k) for k in range(4028)]
tgt_dates  = [dt.date(2004,6,1) + dt.timedelta(days=k) for k in range(92)]
assert base_dates[0].isoformat()=="1991-12-27" and base_dates[-1].isoformat()=="2003-01-05"
assert tgt_dates[0].isoformat()=="2004-06-01" and tgt_dates[-1].isoformat()=="2004-08-31"

# spot-check that file time coordinates match filenames
import h5py
for f in ["sst_19911227.nc","sst_19920229.nc","sst_20021231.nc","sst_20030105.nc","sst_20040601.nc","sst_20040831.nc","sst_20040715.nc"]:
    with h5py.File(os.path.join(BASE,f), "r") as hf:
        t = hf["time"][()]
    tt = np.datetime64(t[0]).astype("datetime64[D]").astype(dt.datetime)
    print(f, "->", tt.date())

# ---------- doy ----------
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mcum = [0] + list(np.cumsum(mlen))
def doy(d): return mcum[d.month-1] + d.day

# ---------- pools ----------
idx_of = {d: k for k, d in enumerate(base_dates)}
pools = {}
for d in base_dates:
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        dd = doy(d)
        if dd == 60: continue
        for k in range(-5,6):
            pools.setdefault(dd, []).append(idx_of[d + dt.timedelta(days=k)])
assert len(pools) == 365 and all(len(v)==121 for v in pools.values())
assert 60 not in pools

# ---------- sea cells ----------
finite_all = np.all(np.isfinite(tgt), axis=0)
sea = np.argwhere(finite_all)
nsea = sea.shape[0]
print("sea cells:", nsea, "of 3600")
cell_flat = sea[:,0]*60 + sea[:,1]

# ---------- independent pool-date check for a few (doy, cell) ----------
# independent construction: for each baseline year, the (month,day) with given doy
md_of_doy = {}
for d in (dt.date(2004,1,1) + dt.timedelta(days=k) for k in range(366)):  # leap template
    md_of_doy[doy(d)] = (d.month, d.day)
import random
random.seed(42)
base_flat = base.reshape(4028, 3600)
for trial in range(5):
    dd = random.choice(sorted(pools))
    m, day = md_of_doy[dd]
    dates = []
    for y in range(1992, 2003):
        a = dt.date(y, m, day)
        for k in range(-5,6):
            dates.append(a + dt.timedelta(days=k))
    idxA = np.array([idx_of[d] for d in dates])
    idxB = np.array(pools[dd])
    assert set(int(x) for x in idxA) == set(int(x) for x in idxB), (dd, )
print("independent pool-date check OK (5 random doys)")
print("elapsed:", time.time()-t_start)
