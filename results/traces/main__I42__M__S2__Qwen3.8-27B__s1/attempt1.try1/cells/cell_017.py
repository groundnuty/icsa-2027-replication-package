import numpy as np, pickle
from collections import defaultdict

base = np.load('/tmp/base.npy')
target = np.load('/tmp/target.npy').reshape(92, -1)
time_all = np.load('/tmp/time_all.npy')
base_dates = time_all[3647:7675]
target_dates = time_all[11109:11201]
thr_s = np.load('/tmp/thr_s.npy')

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates).astype('datetime64[D]')
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

bmin = np.datetime64('1992-01-01'); bmax = np.datetime64('2002-12-31')
pools = defaultdict(list)
for k in range(-5, 6):
    b = base_dates + np.timedelta64(k, 'D')
    msk = (b >= bmin) & (b <= bmax)
    for i, dd in zip(np.where(msk)[0].tolist(), doy366(b[msk]).tolist()):
        pools[dd].append(i)

def hazen_manual(x, p=0.9):
    x = x[~np.isnan(x)]
    if x.size == 0:
        return np.nan
    x = np.sort(x)
    n = x.size
    h = n * p + 0.5          # 1-based, numpy's 'hazen'
    if h >= n:
        return x[-1]
    i0 = int(np.floor(h)); f = h - i0
    return x[i0 - 1] + f * (x[i0] - x[i0 - 1])

cells = [3292, 1798, 5, 1000]
# recompute unsmoothed thr for ALL doys for these cells
thr_u = {}
for c in cells:
    i, j = divmod(c, 60)
    col = np.empty((366, 121))
    ok = True
    for d in list(range(1, 60)) + list(range(61, 367)):
        col[d - 1] = base[pools[d], i, j]
    thr_u[c] = np.array([hazen_manual(col[d - 1]) for d in range(1, 367)])

# corrected hazen check
c = 1798
col = base[pools[153], 29, 58]
print("hazen manual vs numpy:", hazen_manual(col), np.nanquantile(col, 0.9, method='hazen'),
      np.isclose(hazen_manual(col), np.nanquantile(col, 0.9, method='hazen')))

# day-60 fill check
for c in cells:
    t60 = (thr_u[c][58] + thr_u[c][60]) / 2
    print(f"cell {c} day60 fill: manual={t60:.6f} (stored unsmoothed not available; formula check only)")

# smoothing check: recomputed unsmoothed (with day60 fill) vs saved thr_s
for c in cells:
    t = thr_u[c].copy()
    t[59] = (t[58] + t[60]) / 2.0
    off = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
    t_s = t[off].mean(axis=1)
    for d in [153, 228, 244, 1, 366]:
        match = np.isclose(t_s[d - 1], thr_s[d - 1, c], rtol=0, atol=1e-9)
        print(f"cell {c} doy {d}: re-smoothed={t_s[d-1]:.9f} saved={thr_s[d-1, c]:.9f} match={match}")
        assert match

# edge cases over all cells: seed runs count, max non-seed run, merging usage
ND = 92
doy_t = doy366(target_dates)
thr_t = thr_s[doy_t - 1]
hot = (target >= thr_t) & np.isfinite(target) & np.isfinite(thr_t)
sea = np.isfinite(target).all(axis=0)
hot &= sea[None, :]
max_nonseed = 0
n_seed2 = 0
n_merged = 0
for c in range(3600):
    h = hot[:, c]
    i, runs = 0, []
    while i < ND:
        if h[i]:
            j = i
            while j + 1 < ND and h[j + 1]:
                j += 1
            runs.append((j - i + 1, i, j))
            i = j + 1
        else:
            i += 1
    seeds = [r for r in runs if r[0] >= 5]
    nonseeds = [r for r in runs if r[0] < 5]
    max_nonseed = max(max_nonseed, max([r[0] for r in nonseeds], default=0))
    if len(seeds) >= 2:
        n_seed2 += 1
        if any(seeds[k + 1][1] - seeds[k][2] - 1 <= 2 for k in range(len(seeds) - 1)):
            n_merged += 1
print("max non-seed run length:", max_nonseed)
print("cells with >=2 seed runs:", n_seed2, " cells where merging was used:", n_merged)
print("total hot cell-days:", int(hot.sum()))
