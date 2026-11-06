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

# --- 1) hazen reference check ---
q = np.quantile(np.arange(1, 122, dtype=float), 0.9, method="hazen")
print("hazen p90 of 1..121:", q, "(expect 108.5)")
assert abs(q - 108.5) < 1e-12

# --- 2) Feb29 / Mar1 window-membership checks ---
def pool_rows(d):
    b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
    base_idx = np.arange(b0, b1+1)
    bd = doy[base_idx]
    return np.concatenate([np.arange(i-5, i+6) for i in base_idx[bd == d]])

r59, r61 = set(pool_rows(59).tolist()), set(pool_rows(61).tolist())
i_29_96 = d2i[np.datetime64("1996-02-29")]
i_01_93 = d2i[np.datetime64("1993-03-01")]
i_28_93 = d2i[np.datetime64("1993-02-28")]
print("1996-02-29 in pool59:", i_29_96 in r59, "| in pool61:", i_29_96 in r61)
print("1993-03-01 in pool59:", i_01_93 in r59, "| in pool61:", i_01_93 in r61)
print("1993-02-28 in pool59:", i_28_93 in r59, "| in pool61:", i_28_93 in r61)
allp = {d: set(pool_rows(d).tolist()) for d in list(range(1,60)) + list(range(61,367))}
in_other = [d for d, s in allp.items() if d not in (59, 61) and i_29_96 in s]
print("1996-02-29 in any other pool:", in_other)
assert i_29_96 in r59 and i_29_96 in r61 and not in_other
assert i_01_93 in r59 and i_01_93 in r61

# --- 3) brute-force threshold/climatology for 3 sea cells at doy 153 (2004-06-01) ---
sea = np.load("/tmp/mhw/sea.npy")
thr_s = np.load("/tmp/mhw/thr_s.npy")
clim_s = np.load("/tmp/mhw/clim_s.npy")
# recompute pre-smooth for comparison
with np.errstate(all="ignore"):
    pass
cells = [(i, j) for i in range(60) for j in range(60) if sea[i, j]][:3]
for (i, j) in cells:
    vals = []
    for y in range(1992, 2003):
        anchor = dt.date(y, 6, 1)
        for k in range(-5, 6):
            dte = anchor + dt.timedelta(days=k)
            r = d2i[np.datetime64(dte.isoformat())]
            vals.append(sst[r, i, j])
    v = np.array(vals)
    vf = v[~np.isnan(v)]
    n = len(vf)
    # hazen manually: h = n*0.9 - 0.4  (HF type5: h = (n-1)p + 0.5 ... use definition p_i=(i-0.5)/n)
    vs = np.sort(vf)
    h = n*0.9 + 0.5            # hazen plotting position inverted: i = n*p + 0.5
    k0 = int(np.floor(h))
    g = h - k0
    p90 = vs[k0-1] if g == 0 else vs[k0-1] + g*(vs[k0] - vs[k0-1]) if k0 <= n else vs[n-1]
    # numpy check
    p90_np = np.nanpercentile(v, 90, method="hazen")
    mean_np = np.nanmean(v)
    # smoothed expected: mean of pre-smooth doy 138..168 -> need pre-smooth values:
    print(f"cell({i},{j}) lat={sub.latitude.values[i]:.2f} lon={sub.longitude.values[j]:.2f} n={n} "
          f"manual={p90:.4f} np={p90_np:.4f} mean={mean_np:.4f}")
    assert abs(p90 - p90_np) < 1e-9

# verify smoothed value equals mean of 31 pre-smooth days for doy 153
# rebuild pre-smooth thr (fast path) to verify smoothing composition
b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
base_idx = np.arange(b0, b1+1); bd = doy[base_idx]
i, j = cells[0]
pre = []
for d in range(138, 169):
    if d == 60:
        continue
    idxs = base_idx[bd == d]
    rows = np.concatenate([np.arange(x-5, x+6) for x in idxs])
    P = sst[rows, i, j]
    pre.append((d, np.nanpercentile(P, 90, method="hazen"), np.nanmean(P)))
pre = np.array([p[1] for p in pre])
# day60 fix: doy138..168 does not include 60, so pre is direct
print("sm[152] check:", thr_s[152, i, j], "mean of 31 pre:", pre.mean(), "match:", np.allclose(thr_s[152, i, j], pre.mean()))
assert np.allclose(thr_s[152, i, j], pre.mean())
print("ALL VERIFICATION OK")
