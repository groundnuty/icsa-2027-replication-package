import numpy as np, xarray as xr, json, os, warnings, time

t0 = time.time()
sub = xr.open_dataset("/tmp/mhw/subset.nc")
times = sub.time.values          # (4120,) datetime64[ns]
sst   = sub.analysed_sst.values  # (4120, 60, 60) float64
lat, lon = sub.latitude.values, sub.longitude.values
Nc = 60*60
print("loaded", sst.shape, time.time()-t0)

# ---------- day of year (1..366, Feb29=60) ----------
ts = times.astype("datetime64[D]")
yrs = ts.astype("datetime64[Y]")
doy = (ts - yrs).astype("timedelta64[D]").astype(np.int64) + 1
# spot checks
for dt in ["2004-01-01","2004-02-28","2004-02-29","2004-03-01","2000-02-29","2001-03-01","2000-03-01","2002-12-31","1991-12-27"]:
    i = np.searchsorted(ts, np.datetime64(dt))
    print(dt, "-> doy", doy[i], "date ok:", ts[i] == np.datetime64(dt))

# ---------- baseline dates 1992-01-01 .. 2002-12-31 ----------
b0 = np.searchsorted(ts, np.datetime64("1992-01-01"))
b1 = np.searchsorted(ts, np.datetime64("2002-12-31"))
base_idx = np.arange(b0, b1+1)
base_doy = doy[base_idx]
print("baseline days:", len(base_idx), "first/last:", ts[b0], ts[b1])

pool_rows = {}
for d in range(1, 367):
    if d == 60:
        continue
    idxs = base_idx[base_doy == d]
    rows = np.concatenate([np.arange(i-5, i+6) for i in idxs])
    assert rows.min() >= 0 and rows.max() < len(ts)
    pool_rows[d] = rows
lens = {len(v) for v in pool_rows.values()}
print("pool sizes:", lens, "num doys:", len(pool_rows))
assert lens == {121}

# ---------- threshold (hazen p90) and climatology (mean) ----------
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    thr = np.full((366, Nc), np.nan)
    clim = np.full((366, Nc), np.nan)
    for d in range(1, 367):
        if d == 60:
            continue
        P = sst[pool_rows[d]]                      # (121, Nc)
        thr[d-1]  = np.nanpercentile(P, 90, axis=0, method="hazen")
        clim[d-1] = np.nanmean(P, axis=0)
# day 60 = mean of 59 and 61
thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

# ---------- 31-day centred circular moving mean ----------
def smooth366(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs  = np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(ext, axis=0)], axis=0)
    return (cs[31:367] - cs[:366]) / 31.0

# verify smoothing on a synthetic array incl. wrap
a_test = np.arange(366, dtype=float)[:, None]
sm_test = smooth366(a_test)
expect0 = (sum(range(366-15,366)) + sum(range(0,15)) + 0.0)/31
print("smooth check d0:", sm_test[0,0], "expect:", (sum(range(351,366))+sum(range(0,15)))/31)
print("smooth check d150:", sm_test[150,0], "expect:", np.arange(135,166).mean())
assert np.allclose(sm_test[150,0], np.arange(135,166).mean())
assert np.allclose(sm_test[0,0], (np.arange(351,366).sum()+np.arange(0,15).sum())/31)

thr_s  = smooth366(thr)
clim_s = smooth366(clim)
np.save("/tmp/mhw/thr_s.npy", thr_s)
np.save("/tmp/mhw/clim_s.npy", clim_s)
print("computed", time.time()-t0,
      "NaNs in smoothed thr:", int(np.isnan(thr_s).sum()), "in clim:", int(np.isnan(clim_s).sum()))

# ---------- target period ----------
T0 = 4028
tt = sst[T0:]            # (92, Nc)
tt_times = ts[T0:]
doys_t = doy[T0:]
print("target:", tt_times[0], "->", tt_times[-1], "n=", len(tt_times), "doy range:", doys_t.min(), doys_t.max())
sea = np.all(np.isfinite(tt), axis=0)
print("sea cells:", int(sea.sum()), "/", Nc, " excluded:", int((~sea).sum()))
np.save("/tmp/mhw/sea.npy", sea)

# ---------- hot days ----------
thr_t = thr_s[doys_t - 1]          # (92, Nc)
hot = tt >= thr_t                  # NaN comparisons -> False
print("NaN thresholds used:", int(np.isnan(thr_t).sum()), " hot frac:", float(hot[:, sea].mean()))

# ---------- per-cell MHWs ----------
mask = np.zeros((92, 60, 60), dtype=np.uint8)
T = 92
n_cells_with_mhw = 0
max_run = 0
for c in range(Nc):
    if not sea[c]:
        continue
    h = hot[:, c]
    if not h.any():
        continue
    padded = np.concatenate(([False], h, [False]))
    dd = np.diff(padded.astype(np.int8))
    starts = np.where(dd == 1)[0]
    ends   = np.where(dd == -1)[0] - 1
    runs = [(s, e) for s, e in zip(starts, ends) if (e - s + 1) >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    if not merged:
        continue
    n_cells_with_mhw += 1
    i, j = divmod(c, 60)
    for s, e in merged:
        mask[s:e+1, i, j] = 1
        max_run = max(max_run, e - s + 1)
print("cells with >=1 MHW:", n_cells_with_mhw, "max merged run len:", max_run)
np.save("/tmp/mhw/mask.npy", mask)

# ---------- regional events ----------
active = mask.any(axis=1).any(axis=1)
pad = np.concatenate(([False], active, [False]))
dd = np.diff(pad.astype(np.int8))
es = np.where(dd == 1)[0]
ee = np.where(dd == -1)[0] - 1
events = [{"onset": str(tt_times[s].astype('datetime64[D]')),
           "end":   str(tt_times[e].astype('datetime64[D]'))} for s, e in zip(es, ee)]
print("active days:", int(active.sum()), "events:", json.dumps(events))
print("DONE", time.time()-t0)
