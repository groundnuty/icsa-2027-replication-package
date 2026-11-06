import numpy as np, datetime as dt, time
t0 = time.time()

datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
base_win_dates = dates[:n_base_win]
tgt_dates = dates[n_base_win:]
date_to_idx = {d: i for i, d in enumerate(base_win_dates)}
arr_base64 = arr32[:n_base_win].astype(np.float64)

def date_of_doy(year, doy):
    leap = (year%4==0 and (year%100!=0 or year%400==0))
    if doy <= 59: return dt.date(year,1,1) + dt.timedelta(days=doy-1)
    if doy == 60: return dt.date(year,2,29) if leap else None
    return dt.date(year,3,1) + dt.timedelta(days=doy-61)

# recompute pools (same as before)
pools = {}
for doy in range(1, 367):
    if doy == 60: continue
    idxs = []
    for year in range(1992, 2003):
        bd = date_of_doy(year, doy)
        if bd is None: continue
        for off in range(-5, 6):
            j = date_to_idx.get(bd + dt.timedelta(days=off))
            if j is not None: idxs.append(j)
    pools[doy] = np.array(sorted(set(idxs)))

NC = arr_base64.shape[1]*arr_base64.shape[2]
flat = arr_base64.reshape(arr_base64.shape[0], NC)

threshold = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
for doy in range(1, 367):
    if doy == 60: continue
    pool = flat[pools[doy]]                      # (121, NC)
    threshold[doy-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    clim[doy-1] = np.nanmean(pool, axis=0)

# day 60 = mean of days 59 and 61 (0-indexed 58 and 60)
threshold[59] = 0.5*(threshold[58] + threshold[60])
clim[59] = 0.5*(clim[58] + clim[60])
print('day60 imputed; any NaN in threshold:', int(np.isnan(threshold).sum()), 'clim:', int(np.isnan(clim).sum()))

# 31-day wrapped centred moving mean
shifts = np.arange(-15, 16)
idx = (np.arange(366)[:, None] + shifts[None, :]) % 366   # (366, 31)
def smooth(a):  # a: (366, NC)
    return a[idx].mean(axis=1)   # accumulate over 31 shifts
thr_s = smooth(threshold)
clim_s = smooth(clim)
print('smoothing done in', round(time.time()-t0,1), 's')

# reshape to (366, 60, 60)
thr_s3 = thr_s.reshape(366, 60, 60)
clim_s3 = clim_s.reshape(366, 60, 60)

# spot values for a mid-region sea cell on a target day
def mdoy(d):
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    doy_cal = (d - dt.date(d.year,1,1)).days + 1
    return doy_cal + (0 if (d.month<=2 or leap) else 1)
d0 = dt.date(2021,7,15); doy = mdoy(d0)
cell = (30, 30)
print('cell (30,30) doy', doy, 'thr:', thr_s3[doy-1][cell], 'clim:', clim_s3[doy-1][cell])
print('clim range over sea:', np.nanmin(clim_s3), np.nanmax(clim_s3))
np.save('/work/thr_s.npy', thr_s3)
np.save('/work/clim_s.npy', clim_s3)
print('saved')
