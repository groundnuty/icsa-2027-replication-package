import numpy as np, datetime as dt, os, json, time
print('numpy', np.__version__)
t0 = time.time()

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)

win_dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))   # 4028
tgt_dates = list(daterange(dt.date(2009,6,1), dt.date(2009,8,31)))    # 92
print(len(win_dates), len(tgt_dates))

# day of year by (month, day), leap-style: Jan1=1 ... Feb28=59, Feb29=60, Mar1=61 ... Dec31=366
def doy(date):
    return (date.replace(year=2000) - dt.date(2000,1,1)).days + 1

win_doy = np.array([doy(d) for d in win_dates])
tgt_doy = np.array([doy(d) for d in tgt_dates])
print('win doy range', win_doy.min(), win_doy.max(), 'tgt doys', tgt_doy.min(), tgt_doy.max())

SST_win = np.stack([np.load(f'data/crop_{d.strftime("%Y%m%d")}.npy') for d in win_dates]).astype('float64')
SST_tgt = np.stack([np.load(f'data/crop_{d.strftime("%Y%m%d")}.npy') for d in tgt_dates]).astype('float64')
print('SST_win', SST_win.shape, SST_win.dtype, 'SST_tgt', SST_tgt.shape)
np.save('data/SST_win.npy', SST_win); np.save('data/SST_tgt.npy', SST_tgt)

# sea cells: finite on every target day
finite_tgt = np.isfinite(SST_tgt)
sea = finite_tgt.all(axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)

# baseline anchors: 1992-01-01 .. 2002-12-31
win_start = dt.date(1991,12,27)
anchor_idx_by_doy = {}
base_dates = list(daterange(dt.date(1992,1,1), dt.date(2002,12,31)))
for d in base_dates:
    dd = doy(d)
    anchor_idx_by_doy.setdefault(dd, []).append((d - win_start).days)
print('n doys with anchors', len(anchor_idx_by_doy), 'anchors per doy sample d=1:', anchor_idx_by_doy[1])
# pools per doy d (d != 60): union over anchors of [a-5, a+5]
pool_idx = {}
for dd, alist in anchor_idx_by_doy.items():
    if dd == 60:
        continue
    idx = np.concatenate([np.arange(a-5, a+6) for a in sorted(alist)])
    assert idx.min() >= 0 and idx.max() < len(win_dates)
    pool_idx[dd] = idx
sizes = {dd: len(v) for dd, v in pool_idx.items()}
print('pool size set:', set(sizes.values()), 'n doys pooled:', len(pool_idx))

# compute threshold (hazen 90%) and climatology (mean), NaN-ignoring, per cell
n_doy = 366
thr_raw = np.full((n_doy, 60, 60), np.nan)
clim_raw = np.full((n_doy, 60, 60), np.nan)
for dd in sorted(pool_idx):
    vals = SST_win[pool_idx[dd]]          # (121, 60, 60)
    thr_raw[dd-1] = np.nanquantile(vals, 0.90, axis=0, method='hazen')
    clim_raw[dd-1] = np.nanmean(vals, axis=0)

# day 60 = mean of 59 and 61
for arr in (thr_raw, clim_raw):
    arr[59] = (arr[58] + arr[60]) / 2.0

def smooth366(x):  # centred 31-day wrap-around mean, x: (366, 60, 60)
    x_ext = np.concatenate([x[-15:], x, x[:15]], axis=0)   # 396
    c = np.concatenate([np.zeros((1, 60, 60)), np.cumsum(x_ext, axis=0)], axis=0)
    return (c[31:397] - c[0:366]) / 31.0

thr_smooth = smooth366(thr_raw)
clim_smooth = smooth366(clim_raw)
print('compute time %.1f s' % (time.time()-t0))
print('thr_smooth finite:', np.isfinite(thr_smooth).all(axis=(1,2)).sum(), '/366 doys')
print('thr range', np.nanmin(thr_smooth), np.nanmax(thr_smooth))
print('clim range', np.nanmin(clim_smooth), np.nanmax(clim_smooth))
np.savez('data/climthr.npz', thr_raw=thr_raw, clim_raw=clim_raw, thr_smooth=thr_smooth,
         clim_smooth=clim_smooth, sea=sea, tgt_doy=tgt_doy,
         lat=np.load('data/lat_values.npy'), lon=np.load('data/lon_values.npy'),
         win_doy=win_doy)