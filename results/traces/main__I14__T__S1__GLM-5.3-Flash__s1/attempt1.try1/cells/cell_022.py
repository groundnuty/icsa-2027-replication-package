import numpy as np, pandas as pd, pickle, warnings

with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
bdates = A['bdates']; arr_sea = A['arr_sea']
m_start = np.array([1,32,61,92,122,153,183,214,245,275,306,336])
bdoy = m_start[bdates.month.values-1] + bdates.day.values - 1
byear = bdates.year.values

# Exact membership: t in pool(d) <=> exists k in [-5,5]: year(t+k) in 1992..2002 and doy(t+k)==d
mem = np.zeros((len(bdates), 366), dtype=bool)   # mem[i, d-1]
for k in range(-5, 6):
    sh = bdates + pd.Timedelta(days=k)
    sy = sh.year.values
    sdoy = m_start[sh.month.values-1] + sh.day.values - 1
    ok = (sy >= 1992) & (sy <= 2002) & (sdoy != 60)
    mem[ok, sdoy[ok] - 1] = True

# cross-check against independent brute-force enumeration
def pool_dates_bf(d):
    out = set()
    for y in range(1992, 2003):
        mi = int(np.searchsorted(m_start, d, side='right') - 1)
        month, day = mi+1, int(d - m_start[mi] + 1)
        try:
            c = pd.Timestamp(year=y, month=month, day=day)
        except ValueError:
            continue
        for k in range(-5, 6):
            t = c + pd.Timedelta(days=k)
            out.add((t.year, t.month, t.day))
    return out
bad = 0
for d in range(1, 367):
    if d == 60: continue
    sel = mem[:, d-1]
    mine = set(zip(bdates[sel].year, bdates[sel].month, bdates[sel].day))
    if mine != pool_dates_bf(d):
        bad += 1
        if bad <= 3:
            print(f"doy {d}: MISMATCH sizes {len(mine)} vs {len(pool_dates_bf(d))}",
                  sorted(mine ^ pool_dates_bf(d))[:4])
print("exact-calendar membership mismatches vs brute force:", bad)
sizes = mem.sum(axis=0); sizes[59] = 0
print("pool sizes: min", sizes[sizes>0].min(), "max", sizes.max())
for d in [55, 59, 61, 65, 153, 183, 244, 366]:
    print(f"  doy {d}: {int(mem[:, d-1].sum())} dates")

# recompute thresh/clim with exact pools
N = arr_sea.shape[1]
thresh = np.full((366, N), np.nan); clim = np.full((366, N), np.nan)
for d in range(1, 367):
    if d == 60: continue
    pool = arr_sea[mem[:, d-1]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim[d-1]   = np.nanmean(pool, axis=0)
thresh[59] = 0.5*(thresh[58] + thresh[60]); clim[59] = 0.5*(clim[58] + clim[60])
print("any NaN:", bool(np.isnan(thresh).any()), bool(np.isnan(clim).any()))

def smooth31(x):
    ext = np.concatenate([x[-15:], x, x[:15]], axis=0)
    cs = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(ext, axis=0)])
    return (cs[31:] - cs[:-31]) / 31.0
thresh_s = smooth31(thresh); clim_s = smooth31(clim)

# compare with previous (doy-window) version: differences should be confined to ~doys 45-75
dt_ = np.abs(thresh_s - A['thresh_s']); dc = np.abs(clim_s - A['clim_s'])
print("max |delta thresh_s|:", dt_.max(), "at doy", int(np.argmax(dt_.max(axis=1)))+1)
print("max |delta clim_s|:", dc.max(), "at doy", int(np.argmax(dc.max(axis=1)))+1)
rows = np.where((dt_.max(axis=1) > 0) | (dc_.max(axis=1) > 0) if False else (dt_.max(axis=1) > 0))[0] + 1
print("doys with any threshold change:", rows.min(), "..", rows.max(), "count", len(rows))
print("target doy band 153-244 changed?", bool((dt_[152:244].max() > 0) or (dc[152:244].max() > 0)))

with open('/tmp/stepA2.pkl','wb') as fh:
    pickle.dump({'thresh_s': thresh_s, 'clim_s': clim_s, 'sst': A['sst'], 'sea': A['sea'],
                 'tdates': A['tdates'], 'tdoy': A['tdoy'], 'latvals': A['latvals'], 'lonvals': A['lonvals'],
                 'bdates': bdates, 'arr_sea': arr_sea, 'mem': mem}, fh)
print("saved stepA2")
