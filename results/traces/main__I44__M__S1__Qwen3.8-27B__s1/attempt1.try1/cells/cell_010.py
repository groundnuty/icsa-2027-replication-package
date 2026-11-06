import numpy as np, datetime as dt, pickle, time, warnings

t0 = time.time()
warnings.filterwarnings("ignore")

bas = np.load("output/bas_sst.npy").astype(np.float64)
b_ord_arr = np.array([dt.date.fromisoformat(s).toordinal() for s in pickle.load(open("output/bas_days.pkl","rb"))])
b0 = b_ord_arr[0]

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
    assert idx.min() >= b0 and idx.max() <= b_ord_arr[-1]
    vals = bas[idx - b0].reshape(len(idx), -1)
    thr_raw[d-1] = np.nanquantile(vals, 0.9, method="hazen", axis=0)
    clim_raw[d-1] = np.nanmean(vals, axis=0)
    pool_sizes[d] = len(idx)
    if d % 30 == 0:
        np.save("output/thr_raw.npy", thr_raw); np.save("output/clim_raw.npy", clim_raw)
        print("doy", d, "%.1f s" % (time.time()-t0), flush=True)

thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
np.save("output/thr_raw.npy", thr_raw); np.save("output/clim_raw.npy", clim_raw)
np.save("output/pool_sizes.npy", np.array([pool_sizes.get(d, -1) for d in range(1,367)]))
print("pool sizes sample:", {k: pool_sizes[k] for k in (1, 59, 61, 183, 365, 366)})
print("POOL DONE %.1f s" % (time.time()-t0))
