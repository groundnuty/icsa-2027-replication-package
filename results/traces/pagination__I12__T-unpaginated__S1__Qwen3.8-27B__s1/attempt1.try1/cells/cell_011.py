import numpy as np, pickle, datetime as dt, time

t0 = time.time()
a = np.load('/tmp/base_a.npz'); b = np.load('/tmp/base_b.npz'); t = np.load('/tmp/tgt.npz')
base = np.concatenate([a['arr'], b['arr']], axis=0)      # (4028, 60, 60)
bdates = [dt.date.fromisoformat(s) for s in np.concatenate([a['dates'], b['dates']])]
tgt = t['arr']                                            # (92, 60, 60)
tdates = [dt.date.fromisoformat(s) for s in t['dates']]
meta = pickle.load(open('/tmp/region_meta.pkl','rb'))

# ---- day-of-year mapping (Feb28=59, Feb29=60, Mar1=61, Dec31=366) ----
leap = dt.date(2000,1,1)
md_of_doy = {}
doy_of_md = {}
d = leap
while d.year == 2000:
    yday = d.timetuple().tm_yday
    md_of_doy[yday] = (d.month, d.day)
    doy_of_md[(d.month, d.day)] = yday
    d += dt.timedelta(days=1)
def doy(date):  # works for leap & non-leap per the mapping
    return doy_of_md[(date.month, date.day)]
# sanity checks
assert doy(dt.date(2009,1,1))==1 and doy(dt.date(2009,2,28))==59 and doy(dt.date(2009,3,1))==61
assert doy(dt.date(2000,2,29))==60 and doy(dt.date(2009,12,31))==366
assert doy(dt.date(2009,6,1))==152 and doy(dt.date(2009,8,31))==243
assert doy(dt.date(2000,3,1))==61  # Mar 1 = 61 in leap years too

# ---- baseline date -> row ----
brow = {d: i for i, d in enumerate(bdates)}
print('pool-date lookup ok; sample', bdates[0], bdates[-1])

ncells = 3600
thr_raw = np.full((366, ncells), np.nan)
clim_raw = np.full((366, ncells), np.nan)
base_flat = base.reshape(4028, ncells)

t1 = time.time()
for d_ in range(1, 367):
    if d_ == 60:
        continue
    m, dd = md_of_doy[d_]
    idx = []
    for y in range(1992, 2003):
        anchor = dt.date(y, m, dd)
        for k in range(-5, 6):
            idx.append(brow[anchor + dt.timedelta(days=k)])
    idx = np.array(idx)
    D = base_flat[idx]          # (121, ncells)
    thr_raw[d_-1] = np.nanquantile(D, 0.90, axis=0, method='hazen')
    clim_raw[d_-1] = np.nanmean(D, axis=0)
print('pools done', time.time()-t1)

thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

# ---- 31-day centred wrapping moving mean over 366 days ----
def smooth31(raw):
    ext = np.concatenate([raw[-15:], raw, raw[:15]], axis=0)   # (396, n)
    win = np.lib.stride_tricks.sliding_window_view(ext, 31, axis=0)  # (366, 31, n)
    return win.mean(axis=1)
thr_sm = smooth31(thr_raw)
clim_sm = smooth31(clim_raw)
print('smooth done', time.time()-t0)

np.save('/tmp/thr_raw.npy', thr_raw)
np.save('/tmp/thr_sm.npy', thr_sm)
np.save('/tmp/clim_raw.npy', clim_raw)
np.save('/tmp/clim_sm.npy', clim_sm)

finite_tgt = np.all(np.isfinite(tgt), axis=0).reshape(ncells)
sea = np.where(finite_tgt)[0]
print('sea cells:', len(sea))
print('any NaN in smoothed thr (sea cells):', bool(np.isnan(thr_sm[:, sea]).any()))
# sample cell: first sea cell, doy 152 (Jun 1)
c = sea[0]
print('sample cell', c, 'lat', float(meta['lat_vals'][c//60]), 'lon', float(meta['lon_vals'][c%60]))
for dd2 in (152, 197, 243):
    print(f'doy {dd2}: clim_raw={clim_raw[dd2-1,c]:.3f} thr_raw={thr_raw[dd2-1,c]:.3f} | clim_sm={clim_sm[dd2-1,c]:.3f} thr_sm={thr_sm[dd2-1,c]:.3f}')
print('target SST Jun1 that cell:', tgt[0, c//60, c%60])