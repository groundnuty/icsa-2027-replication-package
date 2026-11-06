import numpy as np, datetime as dt

base_sst = np.load('/work/base_sst.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')

def doy_map(d):
    leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    return d.timetuple().tm_yday if (leap or d.month < 3) else d.timetuple().tm_yday + 1

# Independent construction: for each doy D, find reference date in each baseline year, window = r±5 calendar days
def ref_dates(D):
    out = []
    for y in range(1992, 2003):
        # find date in year y with doy_map == D
        d = dt.date(y, 1, 1)
        while d.year == y:
            if doy_map(d) == D:
                out.append(d); break
            d += dt.timedelta(days=1)
    return out

def brute(D, i, j):
    vals = []
    for r in ref_dates(D):
        for k in range(-5, 6):
            d = r + dt.timedelta(days=k)
            if dt.date(1991,12,27) <= d <= dt.date(2003,1,5):
                vals.append(base_sst[(d - dt.date(1991,12,27)).days, i, j])
    return np.array(vals)

def hazen(x, p=0.9):
    x = np.sort(x); n = x.size
    h = n*p + 0.5
    lo = int(np.floor(h)); frac = h - lo
    lo1 = min(max(lo,1), n); hi1 = min(max(lo+1,1), n)
    return x[lo1-1] + frac*(x[hi1-1]-x[lo1-1])

for (i,j) in [(10,20),(0,0),(59,59),(30,30)]:
    rt = np.full(366, np.nan); rc = np.full(366, np.nan); sizes={}
    for D in range(1,367):
        if D == 60: continue
        v = brute(D,i,j); sizes[D]=v.size
        v = v[np.isfinite(v)]
        rt[D-1] = hazen(v); rc[D-1] = v.mean()
    rt[59] = 0.5*(rt[58]+rt[60]); rc[59] = 0.5*(rc[58]+rc[60])
    st = np.array([np.mean([rt[(d+k)%366] for k in range(-15,16)]) for d in range(366)])
    sc = np.array([np.mean([rc[(d+k)%366] for k in range(-15,16)]) for d in range(366)])
    exp_sizes = {D: (33 if D==366 else 121) for D in range(1,367) if D!=60}
    sizes_ok = all(sizes[D]==exp_sizes[D] for D in exp_sizes)
    print(f'cell({i},{j}): pool sizes all as expected: {sizes_ok} | max thr diff {np.abs(thr_s[:,i,j]-st).max():.3e} | max clim diff {np.abs(clim_s[:,i,j]-sc).max():.3e}')
