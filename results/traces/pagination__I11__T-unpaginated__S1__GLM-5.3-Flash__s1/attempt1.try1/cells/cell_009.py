import numpy as np, datetime as dt, json, os, time, warnings

t0 = time.time()
ext = np.load('cache/ext.npy')          # (4028, 60, 60) 1991-12-27..2003-01-05
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
print('ext', ext.shape)
raw_thresh = np.full((366, NY, NX), np.nan)
raw_clim   = np.full((366, NY, NX), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60:
            continue
        pool = ext[np.asarray(pool_idx[d])]
        raw_thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        raw_clim[d-1]   = np.nanmean(pool, axis=0)
print('pools done %.1f s' % (time.time()-t0))

for arr in (raw_thresh, raw_clim):
    arr[59] = 0.5 * (arr[58] + arr[60])

def circ_smooth31(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(pad, axis=0)
    c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    return (c[31:] - c[:-31]) / 31.0

sm_t = circ_smooth31(raw_thresh)
sm_c = circ_smooth31(raw_clim)
# manual verification of the circular window
pad = np.concatenate([raw_thresh[-15:], raw_thresh, raw_thresh[:15]], axis=0)
for i in [0, 1, 59, 182, 350, 365]:
    assert np.array_equal(pad[i:i+31].mean(axis=0), sm_t[i]), i
padc = np.concatenate([raw_clim[-15:], raw_clim, raw_clim[:15]], axis=0)
for i in [0, 59, 182, 365]:
    assert np.array_equal(padc[i:i+31].mean(axis=0), sm_c[i]), i
print('smoothing verified: sm[d] = mean(raw[d-15..d+15] mod 366)')
np.save('cache/raw_thresh.npy', raw_thresh); np.save('cache/raw_clim.npy', raw_clim)
np.save('cache/sm_thresh.npy', sm_t); np.save('cache/sm_clim.npy', sm_c)

tgt = np.load('cache/tgt.npy')
sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', int(sea.sum()))
for lbl, k in [('Jun01 (d153)', 152), ('Jul20 (d200)', 199), ('Aug31 (d244)', 243)]:
    print('%s: smoothed thresh mean %.3f K, clim mean %.3f K' % (lbl, sm_t[k][sea].mean(), sm_c[k][sea].mean()))
print('raw (unsmoothed) Jul20: thresh %.3f, clim %.3f' % (raw_thresh[199][sea].mean(), raw_clim[199][sea].mean()))
# sanity: raw near Jul20 vs smoothed (should be close mid-summer)
print('threshold day-60 fill check (raw[59] vs mean(raw[58],raw[60])):',
      np.allclose(raw_thresh[59], 0.5*(raw_thresh[58]+raw_thresh[60])))
print('finite check: sm_t finite on all sea cells all days:',
      bool(np.isfinite(sm_t[:, sea]).all()), '| sm_c:', bool(np.isfinite(sm_c[:, sea]).all()))
print('total %.1f s' % (time.time()-t0))
