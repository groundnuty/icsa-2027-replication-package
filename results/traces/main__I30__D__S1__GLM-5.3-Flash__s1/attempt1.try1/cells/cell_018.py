import numpy as np, datetime as dt, time

base_sst = np.load('/work/base_sst.npy')
targ_sst = np.load('/work/targ_sst.npy')
START = dt.date(1991,12,27)

def doy_map(d):
    y = d.timetuple().tm_yday
    if not (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) and d.month >= 3:
        return y + 1
    return y

pool = {}
b = dt.date(1992,1,1)
while b <= dt.date(2002,12,31):
    dd = doy_map(b)
    for k in range(-5,6):
        pool.setdefault(dd, set()).add((b + dt.timedelta(days=k) - START).days)
    b += dt.timedelta(days=1)

t0 = time.time()
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60:
        continue  # no pool of its own
    idx = np.array(sorted(pool[d]))
    vals = base_sst[idx]                      # (n, 60, 60)
    thr[d-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(vals, axis=0)
print('computed raw thr/clim in', round(time.time()-t0,1), 's')

# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

# circular 31-day centred moving mean (unweighted), days d-15..d+15 mod 366
kernel_idx = [(np.arange(366) + k) % 366 for k in range(-15, 16)]
K = np.stack(kernel_idx)   # (31, 366)
thr_s = thr[K].mean(axis=0)
clim_s = clim[K].mean(axis=0)
print('smoothed. shapes:', thr_s.shape, clim_s.shape)

# sanity checks
print('thr_s finite everywhere:', np.isfinite(thr_s).all(), 'clim_s finite:', np.isfinite(clim_s).all())
print('thr_s range:', np.nanmin(thr_s), np.nanmax(thr_s))
print('clim_s range:', np.nanmin(clim_s), np.nanmax(clim_s))
# sea cells: finite SST on every target day
sea = np.isfinite(targ_sst).all(axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)
np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s); np.save('/work/sea.npy', sea)
