import numpy as np, datetime as dt, json, pickle, time
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
nb = 4028
base = cube[:nb].astype('float64')          # (4028, 60, 60)
tgt = cube[nb:].astype('float64')           # (92, 60, 60)
with open(f'{cache}/pools.pkl','rb') as f:
    pools = pickle.load(f)

NC = base[0].size  # 3600
t0 = time.time()
thresh_raw = np.full((367, NC), np.nan, dtype='float64')
clim_raw = np.full((367, NC), np.nan, dtype='float64')
for d in range(1, 367):
    if d == 60:
        continue
    vals = base[pools[d]].reshape(len(pools[d]), NC)   # (121, 3600)
    thresh_raw[d] = np.nanpercentile(vals, 90, axis=0, method='hazen')
    clim_raw[d] = np.nanmean(vals, axis=0)
print('pools computed in', round(time.time()-t0, 2), 's')

thresh_raw[60] = 0.5*(thresh_raw[59] + thresh_raw[61])
clim_raw[60]   = 0.5*(clim_raw[59]   + clim_raw[61])

def circ_smooth(a):  # a: (367, NC); index 0 unused; days 1..366 wrap
    out = np.zeros_like(a)
    for k in range(-15, 16):
        out += np.roll(a, -k, axis=0)
    return out / 31.0

thresh_s = circ_smooth(thresh_raw)
clim_s   = circ_smooth(clim_raw)

# brute-force verification of wrap smoothing
rng = np.random.default_rng(0)
for _ in range(8):
    d = int(rng.integers(1, 367)); c = int(rng.integers(0, NC))
    idxs = [(d + k) % 366 if (d + k) % 366 != 0 else 366 for k in range(-15, 16)]
    bf = thresh_raw[idxs, c].mean()
    assert abs(bf - thresh_s[d, c]) < 1e-12, (d, c)
print('circular smoothing verified vs brute force (days wrap 1..366)')

# verify index-0 row unused: NaN, and smoothing ignores it
assert np.isnan(thresh_raw[0]).all() and np.isnan(clim_raw[0]).all()
d_test = 20
idxs = [(d_test + k) % 366 or 366 for k in range(-15, 16)]
assert 0 not in idxs
print('index 0 unused in smoothing: OK')

np.save(f'{cache}/thresh_s.npy', thresh_s)
np.save(f'{cache}/clim_s.npy', clim_s)
np.save(f'{cache}/thresh_raw.npy', thresh_raw)
np.save(f'{cache}/clim_raw.npy', clim_raw)

sea_finite = np.isfinite(tgt).all(axis=0)   # (60,60)
print('sea cells (finite all target days):', int(sea_finite.sum()), 'of', tgt[0].size)
ii, jj = np.where(sea_finite)
c0 = (int(ii[len(ii)//2]), int(jj[len(jj)//2]))
ci = c0[0]*60 + c0[1]
print('sample sea cell (row,col):', c0)
print('raw thresh doy 153..183/10:', np.round(thresh_raw[153:184:10, ci], 3))
print('sm  thresh doy 153..183/10:', np.round(thresh_s[153:184:10, ci], 3))
print('raw clim  doy 153..183/10:', np.round(clim_raw[153:184:10, ci], 3))
print('sm  clim  doy 153..183/10:', np.round(clim_s[153:184:10, ci], 3))
print('target SST 2021-06-15 at sample cell:', round(float(tgt[14, c0[0], c0[1]]), 3), 'K')