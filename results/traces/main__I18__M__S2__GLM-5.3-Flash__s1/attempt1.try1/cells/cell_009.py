import numpy as np, warnings, time as tm

base = np.load("/tmp/base.npy")   # (4028, 60, 60) float64
tgt  = np.load("/tmp/tgt.npy")    # (92, 60, 60) float64
bt = np.load("/tmp/base_times.npy")
tt = np.load("/tmp/tgt_times.npy")

EPOCH = np.datetime64("1970-01-01")
bdates = EPOCH + bt.astype("timedelta64[D]")
tdates = EPOCH + tt.astype("timedelta64[D]")

def doy366(dates):
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    jan1 = (years - 1970).astype("datetime64[Y]")
    doy_std = (dates - jan1).astype(int) + 1
    leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
    return np.where(leap | (doy_std < 60), doy_std, doy_std + 1)

doy_b = doy366(bdates)
doy_t = doy366(tdates)
print("target doys:", doy_t[0], doy_t[1], doy_t[-1])
print("baseline doy range:", doy_b.min(), doy_b.max())

# sanity: values magnitude check
print("SST range in target:", np.nanmin(tgt), np.nanmax(tgt))
print("SST range in baseline:", np.nanmin(base), np.nanmax(base))

baseline_mask = (bdates >= np.datetime64("1992-01-01")) & (bdates <= np.datetime64("2002-12-31"))
print("n baseline proper days:", baseline_mask.sum(), bdates[baseline_mask][0], bdates[baseline_mask][-1])

thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)

t0 = tm.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        members = bt[baseline_mask & (doy_b == d)]
        assert len(members) == 11, (d, len(members))
        pool_days = np.concatenate([np.arange(m-5, m+6) for m in members])
        pool_mask = np.isin(bt, pool_days)
        pool = base[pool_mask]                      # (n, 60, 60)
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pool loop time:", tm.time()-t0)

# day 60 = mean of day 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
np.save("/tmp/thr_raw.npy", thr_raw)
np.save("/tmp/clim_raw.npy", clim_raw)
print("thr sample (cell 30,30), doy 150..160:", np.round(thr_raw[149:160, 30, 30], 4))
print("clim sample (cell 30,30), doy 150..160:", np.round(clim_raw[149:160, 30, 30], 4))
