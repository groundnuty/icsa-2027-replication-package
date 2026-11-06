import numpy as np, xarray as xr, json, warnings, time

t0 = time.time()
sub = xr.open_dataset("/tmp/mhw/subset.nc")
times = sub.time.values
sst   = sub.analysed_sst.values          # (4120, 60, 60) float64
nlat, nlon = sst.shape[1], sst.shape[2]
Nc = nlat*nlon
ts = times.astype("datetime64[D]")

o = (ts - ts.astype("datetime64[Y]")).astype("timedelta64[D]").astype(np.int64) + 1
year = ts.astype("datetime64[Y]").astype(np.int64) + 1970
is_leap = (year % 4 == 0) & ((year % 100 != 0) | (year % 400 == 0))
doy = o + np.where(~is_leap & (o > 59), 1, 0)

d2i = {t: i for i, t in enumerate(ts)}
fails = 0
for dt, exp in [("2000-02-29",60), ("2001-03-01",61), ("2000-03-01",61), ("2002-12-31",366),
                ("2003-01-01",1), ("2004-06-01",153), ("2004-08-31",244), ("2001-02-28",59),
                ("1992-01-01",1), ("2002-02-28",59), ("2000-12-31",366), ("2001-01-01",1),
                ("1999-12-31",366), ("2003-01-05",5), ("1992-02-29",60), ("1993-03-01",61),
                ("2004-02-28",59), ("2004-02-29",60)]:
    i = d2i.get(np.datetime64(dt))
    if i is not None and doy[i] != exp:
        fails += 1; print("FAIL", dt, doy[i], exp)
print("doy checks:", "all ok" if fails == 0 else f"{fails} FAILS")

b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
base_idx = np.arange(b0, b1+1); base_doy = doy[base_idx]
cnt = np.bincount(base_doy, minlength=367)
print("baseline: all d!=60 count 11:", all(cnt[d] == 11 for d in range(1,367) if d != 60), "| doy60:", cnt[60])

pool_rows = {}
for d in range(1, 367):
    if d == 60:
        continue
    idxs = base_idx[base_doy == d]
    rows = np.concatenate([np.arange(i-5, i+6) for i in idxs])
    assert rows.min() >= 0 and rows.max() < len(ts)
    pool_rows[d] = rows
lens = {len(v) for v in pool_rows.values()}
print("pool sizes:", lens); assert lens == {121}

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    thr = np.full((366, nlat, nlon), np.nan)
    clim = np.full((366, nlat, nlon), np.nan)
    for d in range(1, 367):
        if d == 60:
            continue
        P = sst[pool_rows[d]]
        thr[d-1]  = np.nanpercentile(P, 90, axis=0, method="hazen")
        clim[d-1] = np.nanmean(P, axis=0)
thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth366(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs  = np.concatenate([np.zeros((1,) + a.shape[1:]), np.cumsum(ext, axis=0)], axis=0)
    return (cs[31:367] - cs[:366]) / 31.0

a_test = np.arange(366, dtype=float)[:, None]
sm_test = smooth366(a_test)
assert np.allclose(sm_test[150,0], np.arange(135,166).mean())
assert np.allclose(sm_test[0,0], (np.arange(351,366).sum()+np.arange(0,15).sum())/31)
assert np.allclose(sm_test[365,0], (np.arange(350,366).sum()+np.arange(0,1).sum())/31)
print("smooth ok")

thr_s  = smooth366(thr)
clim_s = smooth366(clim)
np.save("/tmp/mhw/thr_s.npy", thr_s)
np.save("/tmp/mhw/clim_s.npy", clim_s)
print("NaNs smoothed thr:", int(np.isnan(thr_s).sum()), "clim:", int(np.isnan(clim_s).sum()), time.time()-t0)

T0 = 4028
tt = sst[T0:]; tt_times = ts[T0:]; doys_t = doy[T0:]
print("target:", tt_times[0], "->", tt_times[-1], "n=", len(tt_times), "doys:", doys_t.min(), doys_t.max())
sea = np.all(np.isfinite(tt), axis=0)          # (60,60)
print("sea cells:", int(sea.sum()), "/", Nc)
np.save("/tmp/mhw/sea.npy", sea)

thr_t = thr_s[doys_t - 1]
hot = tt >= thr_t
print("NaN thresholds in target window:", int(np.isnan(thr_t).sum()), "hot frac (sea):", float(hot[:, sea].mean()))

mask = np.zeros((92, nlat, nlon), dtype=np.uint8)
n_cells_with_mhw = 0; max_run = 0
for i in range(nlat):
    for j in range(nlon):
        if not sea[i, j]:
            continue
        h = hot[:, i, j]
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
        for s, e in merged:
            mask[s:e+1, i, j] = 1
            max_run = max(max_run, e - s + 1)
print("cells with MHW:", n_cells_with_mhw, "max merged run:", max_run, time.time()-t0)
np.save("/tmp/mhw/mask.npy", mask)

active = mask.any(axis=2).any(axis=1)
pad = np.concatenate(([False], active, [False]))
dd = np.diff(pad.astype(np.int8))
es = np.where(dd == 1)[0]
ee = np.where(dd == -1)[0] - 1
events = [{"onset": str(tt_times[s].astype('datetime64[D]')),
           "end":   str(tt_times[e].astype('datetime64[D]'))} for s, e in zip(es, ee)]
print("active days:", int(active.sum()), "events:", json.dumps(events))
print("DONE", time.time()-t0)
