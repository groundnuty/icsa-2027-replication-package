import numpy as np, datetime as dt, json, pickle, time

# --- check hazen percentile against MATLAB quantile semantics ---
x = np.arange(1., 11.)
print('hazen q90 of 1..10:', np.percentile(x, 90, method='hazen'))  # expect 9.1
x2 = np.array([1., 2., 3., 4.])
print('hazen q90 of 1..4:', np.percentile(x2, 90, method='hazen'))  # h=(4-1)*.9+1=3.7 -> 3.7
# with NaN ignored
x3 = np.array([np.nan, 1., 2., 3., 4.])
print('nanpercentile hazen q90:', np.nanpercentile(x3, 90, method='hazen'))

cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
nb = 4028
base = cube[:nb].astype('float64')          # (4028, 60, 60)
tgt = cube[nb:].astype('float64')           # (92, 60, 60)
with open(f'{cache}/pools.pkl','rb') as f:
    pools = pickle.load(f)

NC = base[0].size  # 3600 cells
t0 = time.time()
thresh_raw = np.empty((366, NC), dtype='float64')
clim_raw = np.empty((366, NC), dtype='float64')
for d in range(1, 367):
    if d == 60:
        continue
    vals = base[pools[d]].reshape(len(pools[d]), NC)   # (121, 3600)
    thresh_raw[d] = np.nanpercentile(vals, 90, axis=0, method='hazen')
    clim_raw[d] = np.nanmean(vals, axis=0)
print('pools computed in', round(time.time()-t0, 2), 's')
# any all-NaN pools (should be none)?
print('any NaN in thresh (should be False):', bool(np.isnan(thresh_raw[1:]).any()),
      '| clim:', bool(np.isnan(clim_raw[1:]).any()))
print('pool count check: min pool len =', min(len(pools[d]) for d in range(1,367) if d != 60))

# day 60 <- mean of day 59 and 61
thresh_raw[60] = 0.5*(thresh_raw[59] + thresh_raw[61])
clim_raw[60]   = 0.5*(clim_raw[59]   + clim_raw[61])

# circular centred 31-day moving mean over 366 days
def circ_smooth(a):  # a: (366, NC)
    out = np.zeros_like(a)
    for k in range(-15, 16):
        out += np.roll(a, -k, axis=0)
    return out / 31.0

thresh_s = circ_smooth(thresh_raw)
clim_s   = circ_smooth(clim_raw)

# brute-force check of smoothing on random doy/cell
rng = np.random.default_rng(0)
for _ in range(5):
    d = int(rng.integers(0, 366)); c = int(rng.integers(0, NC))
    idxs = [(d + k) % 366 for k in range(-15, 16)]
    bf = thresh_raw[idxs, c].mean()
    assert abs(bf - thresh_s[d, c]) < 1e-12, (d, c, bf, thresh_s[d, c])
print('circular smoothing verified vs brute force')
# verify scipy equivalent
from scipy.ndimage import uniform_filter1d
chk = uniform_filter1d(thresh_raw, size=31, axis=0, mode='grid-wrap')
print('max |roll - scipy grid-wrap|:', float(np.abs(chk - thresh_s).max()))

np.save(f'{cache}/thresh_s.npy', thresh_s)
np.save(f'{cache}/clim_s.npy', clim_s)
np.save(f'{cache}/thresh_raw.npy', thresh_raw)
np.save(f'{cache}/clim_raw.npy', clim_raw)

# sanity: summer values for a central sea cell
# pick a cell that is sea (finite in target)
sea_finite = np.isfinite(tgt).all(axis=0)   # (60,60)
print('sea cells (finite all target days):', int(sea_finite.sum()))
ii, jj = np.where(sea_finite)
c0 = (ii[len(ii)//2], jj[len(jj)//2])
ci = c0[0]*60 + c0[1]
print('sample cell (row,col):', c0, 'index', ci)
print('raw thresh doy 153..183 every 10:', np.round(thresh_raw[153:184:10, ci], 3))
print('sm  thresh doy 153..183 every 10:', np.round(thresh_s[153:184:10, ci], 3))
print('raw clim  doy 153..183 every 10:', np.round(clim_raw[153:184:10, ci], 3))
print('sm  clim  doy 153..183 every 10:', np.round(clim_s[153:184:10, ci], 3))
print('target SST first day sample cell:', round(float(tgt[0, c0[0], c0[1]]), 3))