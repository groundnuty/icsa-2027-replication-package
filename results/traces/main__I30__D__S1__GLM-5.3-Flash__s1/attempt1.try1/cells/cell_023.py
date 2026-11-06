import numpy as np, datetime as dt

base_sst = np.load('/work/base_sst.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')

def doy_map(d):
    leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    return d.timetuple().tm_yday if (leap or d.month < 3) else d.timetuple().tm_yday + 1

i, j = 10, 20
def brute_raw(doy_target):
    vals = []
    for year in range(1991, 2004):   # include extension years
        d = dt.date(year, 1, 1)
        while d.year == year:
            # restrict to baseline dates + extension windows
            in_baseline = dt.date(1992,1,1) <= d <= dt.date(2002,12,31)
            in_ext_lo = dt.date(1991,12,27) <= d <= dt.date(1991,12,31)
            in_ext_hi = dt.date(2003,1,1) <= d <= dt.date(2003,1,5)
            if in_baseline or in_ext_lo or in_ext_hi:
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

print('pool size doy1 (expect 121):', counts[1], '| doy153 (121):', counts[153], '| doy366 (33):', counts[366], '| doy60:', counts.get(60))
print('MAX thr diff all 366 doys:', np.abs(thr_s[:,i,j]-sm_thr).max())
print('MAX clim diff all 366 doys:', np.abs(clim_s[:,i,j]-sm_clim).max())

# also verify two more cells fully (vectorized brute force per cell)
for (ii, jj) in [(0,0),(59,59),(30,30)]:
    rt = np.full(366, np.nan); rc = np.full(366, np.nan)
    for d in range(1,367):
        if d == 60: continue
        v = []
        for year in range(1991,2004):
            dd = dt.date(year,1,1)
            while dd.year == year:
                if (dt.date(1992,1,1) <= dd <= dt.date(2002,12,31)) or (dt.date(1991,12,27) <= dd <= dt.date(1991,12,31)) or (dt.date(2003,1,1) <= dd <= dt.date(2003,1,5)):
                    if abs(doy_map(dd)-d) <= 5:
                        v.append(base_sst[(dd-dt.date(1991,12,27)).days, ii, jj])
                dd += dt.timedelta(days=1)
        v = np.array(v); v = v[np.isfinite(v)]
        rt[d-1] = hazen(v); rc[d-1] = v.mean()
    rt[59] = 0.5*(rt[58]+rt[60]); rc[59] = 0.5*(rc[58]+rc[60])
    st = np.array([np.mean([rt[(d+k)%366] for k in range(-15,16)]) for d in range(366)])
    sc = np.array([np.mean([rc[(d+k)%366] for k in range(-15,16)]) for d in range(366)])
    print(f'cell({ii},{jj}): max thr diff {np.abs(thr_s[:,ii,jj]-st).max():.3e}, max clim diff {np.abs(clim_s[:,ii,jj]-sc).max():.3e}')
