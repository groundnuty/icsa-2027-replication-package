import numpy as np, datetime as dt

base_sst = np.load('/work/base_sst.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')

def doy_map(d):
    leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    return d.timetuple().tm_yday if (leap or d.month < 3) else d.timetuple().tm_yday + 1

i, j = 10, 20
def brute_raw(doy_target):
    vals = []
    for year in range(1992, 2003):
        d = dt.date(year, 1, 1)
        while d.year == year:
            if abs(doy_map(d) - doy_target) <= 5:
                vals.append(base_sst[(d - dt.date(1991,12,27)).days, i, j])
            d += dt.timedelta(days=1)
    return np.array(vals)

def hazen(x, p=0.9):
    x = np.sort(x); n = x.size
    h = n * p + 0.5
    lo = int(np.floor(h)); frac = h - lo
    lo1 = min(max(lo, 1), n); hi1 = min(max(lo + 1, 1), n)
    return x[lo1-1] + frac * (x[hi1-1] - x[lo1-1])

raw_thr = np.full(366, np.nan); raw_clim = np.full(366, np.nan)
counts = {}
for d in range(1, 367):
    if d == 60: continue
    v = brute_raw(d); counts[d] = v.size
    v = v[np.isfinite(v)]
    raw_thr[d-1] = hazen(v); raw_clim[d-1] = v.mean()
raw_thr[59] = 0.5*(raw_thr[58] + raw_thr[60]); raw_clim[59] = 0.5*(raw_clim[58] + raw_clim[60])
sm_thr  = np.array([np.mean([raw_thr[(d+k) % 366] for k in range(-15,16)]) for d in range(366)])
sm_clim = np.array([np.mean([raw_clim[(d+k) % 366] for k in range(-15,16)]) for d in range(366)])

print('pool size doy1 (expect 121):', counts[1], '| doy 153:', counts[153], '| doy 366 (expect 33):', counts[366])
for d0 in [0, 59, 152, 243, 365]:
    print(f'doy {d0+1}: thr diff={abs(thr_s[d0,i,j]-sm_thr[d0]):.3e} | clim diff={abs(clim_s[d0,i,j]-sm_clim[d0]):.3e}')
print('max thr diff all 366 doys:', np.abs(thr_s[:,i,j]-sm_thr).max())
print('max clim diff all 366 doys:', np.abs(clim_s[:,i,j]-sm_clim).max())
# hazen cross-check against numpy for one pool
v = brute_raw(153); v = v[np.isfinite(v)]
print('hazen manual:', hazen(v), '== numpy:', np.quantile(v, 0.9, method='hazen'))
