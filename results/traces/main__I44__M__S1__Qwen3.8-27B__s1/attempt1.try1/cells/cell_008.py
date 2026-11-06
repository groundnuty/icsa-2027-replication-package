import numpy as np, datetime as dt, pickle, time

t0 = time.time()

bas = np.load("output/bas_sst.npy").astype(np.float64)          # (4028, 60, 60)
tgt = np.load("output/tgt_sst.npy").astype(np.float64)          # (92, 60, 60)
with open("output/bas_days.pkl", "rb") as fh: bas_days = pickle.load(fh)
with open("output/tgt_days.pkl", "rb") as fh: tgt_days = pickle.load(fh)
b_ord_arr = np.array([dt.date.fromisoformat(d).toordinal() for d in bas_days])
b0 = b_ord_arr[0]

# ---- sea cells: finite on every target day
cell_fin = np.isfinite(tgt).all(axis=0)
n_sea = int(cell_fin.sum())
print("sea cells:", n_sea, "of", cell_fin.size)

baseline_years = list(range(1992, 2003))
def isleap(y): return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)

thr_raw = np.full((366, 60*60), np.nan)
clim_raw = np.full((366, 60*60), np.nan)
pool_sizes = {}
for d in range(1, 367):
    if d == 60:
        continue
    b_dates = []
    for y in baseline_years:
        if d <= 365:
            b = dt.date(y,1,1) + dt.timedelta(days=d-1)
        else:
            if isleap(y):
                b = dt.date(y,12,31)
            else:
                continue
        b_dates.append(b)
    idx_set = set()
    for b in b_dates:
        o = b.toordinal()
        for k in range(-5, 6):
            idx_set.add(o + k)
    idx = np.array(sorted(idx_set))
    assert idx.min() >= b0 and idx.max() <= b_ord_arr[-1], (d, idx.min()-b0, idx.max()-b_ord_arr[-1])
    rel = idx - b0
    vals = bas[rel].reshape(len(idx), -1)
    thr_raw[d-1] = np.nanquantile(vals, 0.9, method="hazen", axis=0)
    clim_raw[d-1] = np.nanmean(vals, axis=0)
    pool_sizes[d] = len(idx)
    if d % 50 == 0:
        print("doy", d, "pool days", len(idx), "%.1f s" % (time.time()-t0), flush=True)

thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print("pool sizes sample:", {k: pool_sizes[k] for k in (1, 59, 60, 61, 183, 365, 366)})
print("nan thr per doy count (max):", int(np.isnan(thr_raw).sum(axis=1).max()))
np.save("output/thr_raw.npy", thr_raw)
np.save("output/clim_raw.npy", clim_raw)
print("done raw %.1f s" % (time.time()-t0))
