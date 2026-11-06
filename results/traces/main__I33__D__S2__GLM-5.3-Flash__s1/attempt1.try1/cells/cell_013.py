import numpy as np
from datetime import date, timedelta
from scipy.ndimage import uniform_filter1d
ext = np.load('/work/ext.npy')

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
np.save('/work/pool.npy', np.array([pool[d] for d in range(1, 367)], dtype=object), allow_pickle=True)

clim_raw = np.full((366, 60, 60), np.nan); thr_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = ext[np.asarray(pool[d])]
    with np.errstate(all='ignore'):
        clim_raw[d-1] = np.nanmean(vals, axis=0)
        thr_raw[d-1]  = np.nanpercentile(vals, 90, axis=0, method='hazen')
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
thr_raw[59]  = 0.5*(thr_raw[58]  + thr_raw[60])
np.save('/work/clim_raw.npy', clim_raw); np.save('/work/thr_raw.npy', thr_raw)

def circ_smooth31(x):
    a = np.concatenate([x[-15:], x, x[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+x.shape[1:]), np.cumsum(a, axis=0)], axis=0)
    j = np.arange(1, 367) + 14
    return (c[j+16] - c[j-15]) / 31.0

clim_sm = circ_smooth31(clim_raw); thr_sm = circ_smooth31(thr_raw)
np.save('/work/clim_sm.npy', clim_sm); np.save('/work/thr_sm.npy', thr_sm)

land = np.isnan(clim_sm[0]); sea = ~land
print('sea cells:', sea.sum(), '| land:', land.sum())
i_s, j_s = np.where(sea); sel = (i_s % 9 == 0) & (j_s % 9 == 0)
cells = list(zip(i_s[sel], j_s[sel]))
for name, arr in [('clim', clim_sm), ('thr', thr_sm)]:
    ref = np.stack([arr[:, i, j] for i, j in cells], axis=1)
    s2 = np.stack([uniform_filter1d(arr[:, i, j], size=31, mode='wrap') for i, j in cells], axis=1)
    print(name, 'scipy wrap max abs diff:', np.abs(ref - s2).max())
# manual check on 3 cells using freshly saved raw
raw = clim_raw.copy()
for i, j in cells[:3]:
    x = clim_sm[:, i, j]
    man = np.array([np.nanmean(raw[(np.arange(d-15, d+16)) % 366, i, j]) for d in range(1, 367)])
    assert np.abs(x - man).max() < 1e-9
print('manual loop check on 3 cells: OK')
print('day-to-day max jumps (sea):', np.abs(np.diff(clim_sm[:, sea], axis=0)).max(), np.abs(np.diff(thr_sm[:, sea], axis=0)).max())
print('clim_sm doy153 @30,30: %.4f | thr_sm doy153 @30,30: %.4f' % (clim_sm[152,30,30], thr_sm[152,30,30]))