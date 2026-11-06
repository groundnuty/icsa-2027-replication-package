import numpy as np, datetime as dt

base_sst = np.load('/work/base_sst.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')

def doy_map(d):
    y = d.timetuple().tm_yday
    leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    return y if (leap or d.month < 3) else y + 1

# independent brute force for one cell (i=10, j=20) and doys 153, 1, 244, 366
i, j = 10, 20
def brute_raw(doy_target):
    # collect values by pure date arithmetic, independent of pool sets
    vals = []
    for year in range(1992, 2003):
        for dmon, dday in [(12,31)] if False else []:
            pass
    # build all baseline dates 1992-01-01..2002-12-31 lazily per year month/day
    for year in range(1992, 2003):
        d = dt.date(year, 1, 1)
        while d.year == year:
            if abs(doy_map(d) - doy_target) <= 5 or (doy_map(d) - doy_target) % 366 <= 5 or (doy_target - doy_map(d)) % 366 <= 5:
                idx = (d - dt.date(1991,12,27)).days
                vals.append(base_sst[idx, i, j])
            d += dt.timedelta(days=1)
    return np.array(vals)

def hazen(x, p=0.9):
    x = np.sort(x)
    n = x.size
    h = n * p + 0.5   # 1-based position (Hyndman-Fan type 5)
    lo = int(np.floor(h)); frac = h - lo
    lo1 = min(max(lo, 1), n); hi1 = min(max(lo+1, 1), n)
    return x[lo1-1] + frac * (x[hi1-1] - x[lo1-1])

# raw thr/clim recompute for full year for this cell, brute force
raw_thr = np.full(366, np.nan); raw_clim = np.full(366, np.nan)
for d in range(1, 367):
    if d == 60: continue
    v = brute_raw(d)
    v = v[np.isfinite(v)]
    raw_thr[d-1] = hazen(v)
    raw_clim[d-1] = v.mean()
raw_thr[59] = 0.5*(raw_thr[58] + raw_thr[60])
raw_clim[59] = 0.5*(raw_clim[58] + raw_clim[60])
sm_thr = np.array([raw_thr[(np.arange(366)+k) % 366].mean() for k in range(-15,16)])
sm_clim = np.array([raw_clim[(np.arange(366)+k) % 366].mean() for k in range(-15,16)])

dchk = [0, 59, 152, 243, 365]
for d0 in dchk:
    print(f'doy {d0+1}: thr mine={thr_s[d0,i,j]:.10f} brute={sm_thr[d0]:.10f} diff={abs(thr_s[d0,i,j]-sm_thr[d0]):.3e} | clim mine={clim_s[d0,i,j]:.10f} brute={sm_clim[d0]:.10f} diff={abs(clim_s[d0,i,j]-sm_clim[d0]):.3e}')
print('max thr diff all doys:', np.abs(thr_s[:,i,j]-sm_thr).max())
print('max clim diff all doys:', np.abs(clim_s[:,i,j]-sm_clim).max())
# hazen spot-check for doy 153
v = brute_raw(153); v = v[np.isfinite(v)]
print('n pool doy153:', v.size, 'hazen manual:', hazen(v), 'numpy:', np.quantile(v, 0.9, method='hazen'))
