import numpy as np, xarray as xr, datetime as dt

sub = xr.open_dataset("/tmp/mhw/subset.nc")
times = sub.time.values
sst = sub.analysed_sst.values
ts = times.astype("datetime64[D]")
o = (ts - ts.astype("datetime64[Y]")).astype("timedelta64[D]").astype(np.int64) + 1
year = ts.astype("datetime64[Y]").astype(np.int64) + 1970
is_leap = (year % 4 == 0) & ((year % 100 != 0) | (year % 400 == 0))
doy = o + np.where(~is_leap & (o > 59), 1, 0)
d2i = {t: i for i, t in enumerate(ts)}

# HF type 5 (Hazen): i = n*p + 0.5 (1-based)
def hazen_p90_manual(v):
    vf = np.sort(v[~np.isnan(v)])
    n = len(vf)
    if n == 0: return np.nan
    h = n*0.9 + 0.5
    if h >= n: return vf[n-1]
    k = int(np.floor(h))          # 1-based
    g = h - k
    if g == 0: return vf[k-1]
    return vf[k-1] + g*(vf[k] - vf[k-1])

v121 = np.arange(1, 122, dtype=float)
print("manual hazen 1..121:", hazen_p90_manual(v121), "numpy:", np.nanpercentile(v121, 90, method="hazen"))
assert abs(hazen_p90_manual(v121) - 109.4) < 1e-12
# with NaNs
vnan = np.concatenate([v121, [np.nan, np.nan]])
print("with NaNs manual:", hazen_p90_manual(vnan), "numpy:", np.nanpercentile(vnan, 90, method="hazen"))
assert abs(hazen_p90_manual(vnan) - np.nanpercentile(vnan, 90, method="hazen")) < 1e-12

# --- Feb29 / Mar1 window-membership checks ---
def pool_rows(d):
    b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
    base_idx = np.arange(b0, b1+1)
    bd = doy[base_idx]
    return np.concatenate([np.arange(i-5, i+6) for i in base_idx[bd == d]])

r59, r61 = set(pool_rows(59).tolist()), set(pool_rows(61).tolist())
i_29_96 = d2i[np.datetime64("1996-02-29")]
i_01_93 = d2i[np.datetime64("1993-03-01")]
print("1996-02-29 in pool59:", i_29_96 in r59, "| in pool61:", i_29_96 in r61)
print("1993-03-01 in pool59:", i_01_93 in r59, "| in pool61:", i_01_93 in r61)
in_other = [d for d in list(range(1,60)) + list(range(61,367)) if d not in (59,61) and i_29_96 in set(pool_rows(d).tolist())]
print("1996-02-29 in any other pool:", in_other)
assert i_29_96 in r59 and i_29_96 in r61 and not in_other
assert i_01_93 in r59 and i_01_93 in r61

# --- brute-force threshold/climatology for 3 sea cells at doy 153 ---
sea = np.load("/tmp/mhw/sea.npy")
thr_s = np.load("/tmp/mhw/thr_s.npy")
clim_s = np.load("/tmp/mhw/clim_s.npy")
cells = [(i, j) for i in range(60) for j in range(60) if sea[i, j]][:3]
for (i, j) in cells:
    vals = []
    for y in range(1992, 2003):
        anchor = dt.date(y, 6, 1)
        for k in range(-5, 6):
            dte = anchor + dt.timedelta(days=k)
            vals.append(sst[d2i[np.datetime64(dte.isoformat())], i, j])
    v = np.array(vals)
    m = hazen_p90_manual(v)
    p_np = np.nanpercentile(v, 90, method="hazen")
    c_np = np.nanmean(v)
    print(f"cell({i},{j}) nfin={int(np.isfinite(v).sum())} hazen manual={m:.5f} numpy={p_np:.5f} clim={c_np:.5f}")
    assert abs(m - p_np) < 1e-9

# --- verify smoothing composition for doy 153 (index 152) ---
b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
base_idx = np.arange(b0, b1+1); bd = doy[base_idx]
i, j = cells[0]
pres = []
for d in range(138, 169):
    idxs = base_idx[bd == d]
    rows = np.concatenate([np.arange(x-5, x+6) for x in idxs])
    P = sst[rows, i, j]
    pres.append(np.nanpercentile(P, 90, method="hazen"))
print("sm[152]:", thr_s[152, i, j], "mean(31 pre):", float(np.mean(pres)), "match:", np.allclose(thr_s[152, i, j], float(np.mean(pres))))
assert np.allclose(thr_s[152, i, j], float(np.mean(pres)))

# --- also verify clim smoothing for a doy near wrap? doy 153 is fine; check doy 366 wrap with cell 0 (land ok, just arithmetic) ---
pres366 = []
for d in list(range(351, 367)):
    idxs = base_idx[bd == d]
    rows = np.concatenate([np.arange(x-5, x+6) for x in idxs])
    P = sst[rows, 0, 0]
    pres366.append(np.nanpercentile(P, 90, method="hazen"))
pres366 += [np.nanpercentile(sst[np.concatenate([np.arange(x-5,x+6) for x in base_idx[bd == d]]), 0, 0], 90, method="hazen") for d in range(1, 16)]
print("wrap sm[365]:", thr_s[365, 0, 0], "mean(31 pre):", float(np.mean(pres366)), "match:", np.allclose(thr_s[365, 0, 0], float(np.mean(pres366))))
assert np.allclose(thr_s[365, 0, 0], float(np.mean(pres366)))
print("ALL VERIFICATION OK")
