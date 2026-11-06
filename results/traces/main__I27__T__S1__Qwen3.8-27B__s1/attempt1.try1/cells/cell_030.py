
import numpy as np, datetime as dt, warnings

B = np.concatenate([np.load(f'/tmp/mhw/baseline_part{i}.npy') for i in range(9)], axis=0)
bdates = [dt.date(1991,12,27) + dt.timedelta(days=i) for i in range(B.shape[0])]
bidx = {d: i for i, d in enumerate(bdates)}
thr_raw = np.load('/tmp/mhw/thr_raw.npy')
clim_raw = np.load('/tmp/mhw/clim_raw.npy')
thr_s = np.load('/tmp/mhw/thr_s.npy')
clim_s = np.load('/tmp/mhw/clim_s.npy')
sea2 = np.load('/tmp/mhw/sea2.npy')
maskA = np.load('/tmp/mhw/maskA.npy')
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(92)]

def brute_pool(doy_target, cell):
    # find (month, day) of doy in leap calendar
    cum = [0,31,60,91,121,152,182,213,244,274,305,335]
    m = 1
    while cum[m] < doy_target: m += 1
    day = doy_target - cum[m-1]
    vals = []
    for y in range(1992, 2003):
        if m == 2 and day == 29:
            continue  # day 60 handled separately
        b = dt.date(y, m, day)
        for delta in range(-5, 6):
            t = b + dt.timedelta(days=delta)
            vals.append(B[bidx[t], cell//60, cell%60])
    return np.array(vals)

rng = np.random.default_rng(42)
cells = np.where(sea2)[0]
test_cells = rng.choice(cells, size=4, replace=False)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    for d in [153, 154, 61, 59, 244]:
        for c in test_cells:
            pool = brute_pool(d, c)
            v1 = np.nanquantile(pool, 0.9, method='hazen')
            v2 = thr_raw[d-1, c]
            m1 = np.nanmean(pool); m2 = clim_raw[d-1, c]
            ok = np.isclose(v1, v2) and np.isclose(m1, m2) and pool.size == 121
            if not ok:
                print("MISMATCH", d, c, v1, v2, m1, m2, pool.size)
    print("brute-force pool check done (silence above = all match)")

# smoothing check at doy 153 (idx 152) and wrap doy 5 (idx 4: uses days 366-15..6)
for di, (lo, hi) in {152: (137, 168), 4: None}.items():
    c = test_cells[0]
    if di == 152:
        expect = thr_raw[137:168, c].mean()
    else:
        idxw = [(4 + j) % 366 for j in range(-15, 16)]
        expect = thr_raw[idxw, c].mean()
    print(f"smooth check doy idx {di}: thr_s={thr_s[di, c]:.9f} expect={expect:.9f} match={np.isclose(thr_s[di,c], expect)}")

# event 1 start: first 16 days
active = maskA.any(axis=1)
for k in range(16):
    print(tdates[k], "hot:", int((hot:=None) or 0), end=" ")
print()
hot = np.load('/tmp/mhw/hot.npy')
for k in range(16):
    print(tdates[k], "hot:", int(hot[k].sum()), "mhw:", int(maskA[k].sum()), "active:", bool(active[k]))
