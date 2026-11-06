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

def hazen_p90_manual(v):
    vf = np.sort(v[~np.isnan(v)])
    n = len(vf)
    if n == 0: return np.nan
    h = n*0.9 + 0.5
    if h >= n: return vf[n-1]
    k = int(np.floor(h)); g = h - k
    if g == 0: return vf[k-1]
    return vf[k-1] + g*(vf[k] - vf[k-1])

assert abs(hazen_p90_manual(np.arange(1,122.)) - np.nanpercentile(np.arange(1,122.), 90, method="hazen")) < 1e-12
print("hazen manual == numpy: ok")

def pool_rows(d):
    b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
    base_idx = np.arange(b0, b1+1)
    bd = doy[base_idx]
    return np.concatenate([np.arange(i-5, i+6) for i in base_idx[bd == d]])

# window membership: Feb29 1996 in pools of doys 55..59, 61..65 only
i_29_96 = d2i[np.datetime64("1996-02-29")]
members = [d for d in list(range(1,60))+list(range(61,367)) if i_29_96 in set(pool_rows(d).tolist())]
print("1996-02-29 member of pools:", members)
assert members == [55,56,57,58,59,61,62,63,64,65]

# brute-force threshold/climatology at doy 153 for 3 sea cells
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
    m = hazen_p90_manual(v); p_np = np.nanpercentile(v, 90, method="hazen"); c_np = np.nanmean(v)
    print(f"cell({i},{j}) lat={sub.latitude.values[i]:.4f} lon={sub.longitude.values[j]:.4f} nfin={int(np.isfinite(v).sum())} hazen={p_np:.5f} clim={c_np:.5f}")
    assert abs(m - p_np) < 1e-9

# smoothing composition, doy 153 (index 152): mean of pre-smooth doys 138..168
b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
base_idx = np.arange(b0, b1+1); bd = doy[base_idx]
i, j = cells[0]
pres = []
for d in range(138, 169):
    rows = pool_rows(d)
    pres.append(np.nanpercentile(sst[rows, i, j], 90, method="hazen"))
assert np.allclose(thr_s[152, i, j], float(np.mean(pres)))
print("smoothing composition doy153: ok")

# wrap check at doy 366 (index 365) for cell (0,0) (arithmetic check)
pres366 = [np.nanpercentile(sst[pool_rows(d), 0, 0], 90, method="hazen") for d in list(range(351,367)) + list(range(1,16))]
assert np.allclose(thr_s[365, 0, 0], float(np.mean(pres366)))
print("smoothing composition doy366 (wrap): ok")

# day-60 rule check: thr[59] (pre-smooth) == mean(thr[58], thr[60]) pre-smooth
pre58 = np.nanpercentile(sst[pool_rows(59)], 90, method="hazen")
pre60 = np.nanpercentile(sst[pool_rows(61)], 90, method="hazen")
# pre-smooth thr at 60 would be (pre58+pre60)/2; check via smoothed value at index 59:
# sm[59] = mean over doys 44..74 of pre-smooth; reconstruct fully:
pre = np.full(366, np.nan)
for d in list(range(1,60))+list(range(61,367)):
    pre[d-1] = np.nanpercentile(sst[pool_rows(d), 5, 5], 90, method="hazen")
pre[59] = 0.5*(pre[58] + pre[60])
idx = (59-15+np.arange(31)) % 366
assert np.allclose(thr_s[59, 5, 5], pre[idx].mean())
print("day-60 rule + smoothing at doy60: ok")
print("ALL VERIFICATION OK")
