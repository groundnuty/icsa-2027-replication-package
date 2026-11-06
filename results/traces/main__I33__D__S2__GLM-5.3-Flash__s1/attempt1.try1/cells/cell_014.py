import numpy as np
from datetime import date, timedelta
ext = np.load('/work/ext.npy')
print('ext all finite:', np.isfinite(ext).all())

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
for d in range(1, 367):
    if d == 60: continue
    vals = ext[np.asarray(pool[d])]
    with np.errstate(all='ignore'):
        clim_raw[d-1] = np.nanmean(vals, axis=0)
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

def circ_smooth31(x):
    a = np.concatenate([x[-15:], x, x[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+x.shape[1:]), np.cumsum(a, axis=0)], axis=0)
    j = np.arange(1, 367) + 14
    return (c[j+16] - c[j-15]) / 31.0

clim_sm = circ_smooth31(clim_raw)
# check one specific cell thoroughly
i, j = 0, 0  # corner
x_raw = clim_raw[:, i, j]; x_sm = clim_sm[:, i, j]
man = np.array([np.nanmean(x_raw[(np.arange(d-15, d+16)) % 366]) for d in range(1, 367)])
diff = np.abs(x_sm - man)
print('cell(0,0) max diff:', np.nanmax(diff), '| nans in raw:', np.isnan(x_raw).sum(), '| nans in sm:', np.isnan(x_sm).sum())
bad = np.where(diff > 1e-9)[0]
print('bad doys (first 10):', bad[:10]+1)
# where do raw NaNs appear across the field?
print('raw NaN cells:', np.isnan(clim_raw[0]).sum())
# compare my smoothing vs manual for a NON-nan random segment of x_raw
k = 200
print('doy201: mine %.10f manual %.10f' % (x_sm[200], man[200]))
print('raw window doy201:', x_raw[(np.arange(200-15, 200+16)) % 366][:8], '...')
# Is the issue cumsum precision with 30-day windows of ~281? no. Print c check:
a = np.concatenate([x_raw[-15:], x_raw, x_raw[:15]])
print('manual window sum vs c-based:', np.sum(x_raw[(np.arange(199-15, 199+16)) % 366]), (np.cumsum(a)[199+31] - np.cumsum(a)[199]))