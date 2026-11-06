import numpy as np, datetime as dt, json, time, warnings

t0 = time.time()
ext = np.load('cache/ext.npy')
meta = json.load(open('cache/meta.json'))
dates_ext = [dt.date.fromisoformat(s) for s in meta['dates_ext']]
B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)
cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def md_doy(d): return int(cum[d.month-1] + d.day)

pool_idx = {d: [] for d in range(1, 367) if d != 60}
for i, x in enumerate(dates_ext):
    for o in range(-5, 6):
        z = x + dt.timedelta(days=o)
        if B0 <= z <= B1 and not (z.month == 2 and z.day == 29):
            pool_idx[md_doy(z)].append(i)
assert all(len(v) == 121 for v in pool_idx.values())

NT, NY, NX = ext.shape
raw_thresh = np.full((366, NY, NX), np.nan)
raw_clim   = np.full((366, NY, NX), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        pool = ext[np.asarray(pool_idx[d])]
        raw_thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        raw_clim[d-1]   = np.nanmean(pool, axis=0)
for arr in (raw_thresh, raw_clim):
    arr[59] = 0.5 * (arr[58] + arr[60])
np.save('cache/raw_thresh.npy', raw_thresh); np.save('cache/raw_clim.npy', raw_clim)
print('pools + day-60 fill done and saved, %.1f s' % (time.time()-t0))

def smooth_cumsum(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(pad, axis=0); c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    return (c[31:] - c[:-31]) / 31.0
def smooth_direct(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    win = np.stack([pad[i:i+31] for i in range(366)], axis=0)
    return win.mean(axis=1)

for name, arr in [('thresh', raw_thresh), ('clim', raw_clim)]:
    s1, s2 = smooth_cumsum(arr), smooth_direct(arr)
    diff = np.abs(s1 - s2)
    pad = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    ok = all(np.array_equal(pad[i:i+31].mean(axis=0), s2[i]) for i in [0,1,59,182,350,365])
    print('%s: max|cumsum-direct| = %.3e, differing elems = %d, direct==manual-window everywhere probed: %s'
          % (name, diff.max(), int((diff>0).sum()), ok))
    np.save(f'cache/sm_{name}.npy', s2.astype(np.float64))
print('saved sm_thresh.npy / sm_clim.npy (direct method), %.1f s' % (time.time()-t0))

tgt = np.load('cache/tgt.npy')
sea = np.isfinite(tgt).all(axis=0)
sm_t = np.load('cache/sm_thresh.npy'); sm_c = np.load('cache/sm_clim.npy')
for lbl, k in [('Jun01 d153', 152), ('Jul20 d200', 199), ('Aug31 d244', 243)]:
    print('%s: smoothed thresh %.3f K | smoothed clim %.3f K' % (lbl, sm_t[k][sea].mean(), sm_c[k][sea].mean()))
print('raw Jul20: thresh %.3f | clim %.3f' % (raw_thresh[199][sea].mean(), raw_clim[199][sea].mean()))
print('sea cells:', int(sea.sum()), '| all finite:', bool(np.isfinite(sm_t[:,sea]).all() and np.isfinite(sm_c[:,sea]).all()))
print('total %.1f s' % (time.time()-t0))
