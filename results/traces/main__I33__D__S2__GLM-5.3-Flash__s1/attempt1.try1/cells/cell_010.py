import numpy as np
ext = np.load('/work/ext.npy')
pool = np.load('/work/pool.npy', allow_pickle=True).item() if False else None
# rebuild pools (corrected) quickly and cache as arrays
from datetime import date, timedelta
def doy_of(y,m,d): return (date(2000,m,d) - date(2000,1,1)).days + 1
d0 = date(1992,1,1); d1 = date(2002,12,31)
base_dates = [d0 + timedelta(days=k) for k in range((d1-d0).days + 1)]
e0 = date(1991,12,27)
def eidx(dt): return (dt - e0).days
pool = {d: [] for d in range(1, 367)}
for b in base_dates:
    bd = doy_of(b.year, b.month, b.day)
    if bd == 60: continue
    for o in range(-5, 6):
        pool[bd].append(eidx(b + timedelta(days=o)))

clim_raw = np.full((366, 60, 60), np.nan)
thr_raw  = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = ext[np.asarray(pool[d])]
    with np.errstate(all='ignore'):
        clim_raw[d-1] = np.nanmean(vals, axis=0)
        thr_raw[d-1]  = np.nanpercentile(vals, 90, axis=0, method='hazen')

# day 60 = mean of days 59 and 61 (per cell)
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
thr_raw[59]  = 0.5*(thr_raw[58]  + thr_raw[60])

def circ_smooth31(x):  # x: (366, ...) centred 31-day mean, wrapping mod 366
    a = np.concatenate([x[-15:], x, x[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+x.shape[1:]), np.cumsum(a, axis=0)], axis=0)
    j = np.arange(1, 367) + 14          # padded centre index for each doy
    return (c[j+16] - c[j-15]) / 31.0

clim_sm = circ_smooth31(clim_raw)
thr_sm  = circ_smooth31(thr_raw)
np.save('/work/clim_sm.npy', clim_sm); np.save('/work/thr_sm.npy', thr_sm)

# verify smoothing against scipy if available
try:
    from scipy.ndimage import uniform_filter1d
    s2 = np.stack([uniform_filter1d(clim_raw[:,i,j], size=31, mode='wrap') for i in range(0,60,7) for j in range(0,60,7)], axis=1)
    ref = np.stack([clim_sm[:,i,j] for i in range(0,60,7) for j in range(0,60,7)], axis=1)
    print('scipy cross-check max abs diff:', np.abs(s2-ref).max())
except Exception as e:
    print('scipy unavailable:', e)
# sanity: smoothness and sample values
print('clim_sm day-to-day max jump:', np.abs(np.diff(clim_sm, axis=0)).max())
print('thr_sm  day-to-day max jump:', np.abs(np.diff(thr_sm, axis=0)).max())
print('sample sea cell [30,30]: clim doy153 %.4f doy1 %.4f | thr doy153 %.4f doy1 %.4f' %
      (clim_sm[152,30,30], clim_sm[0,30,30], thr_sm[152,30,30], thr_sm[0,30,30]))
print('land cells NaN everywhere:', np.isnan(clim_sm).sum(axis=0)[~np.isnan(clim_sm[0])].size == 0, '| total NaN cells:', np.isnan(clim_sm[0]).sum())