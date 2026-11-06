import numpy as np, datetime as dt, json, pickle, time, warnings
warnings.filterwarnings('ignore')

cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
nb = 4028
base = cube[:nb].astype('float64')
tgt = cube[nb:].astype('float64')
with open(f'{cache}/pools.pkl','rb') as f:
    pools = pickle.load(f)

NC = base[0].size  # 3600
t0 = time.time()
thresh_raw = np.full((367, NC), np.nan, dtype='float64')
clim_raw = np.full((367, NC), np.nan, dtype='float64')
for d in range(1, 367):
    if d == 60:
        continue
    vals = base[pools[d]].reshape(len(pools[d]), NC)
    thresh_raw[d] = np.nanpercentile(vals, 90, axis=0, method='hazen')
    clim_raw[d] = np.nanmean(vals, axis=0)
print('pools computed in', round(time.time()-t0, 2), 's')

thresh_raw[60] = 0.5*(thresh_raw[59] + thresh_raw[61])
clim_raw[60]   = 0.5*(clim_raw[59]   + clim_raw[61])
np.save(f'{cache}/thresh_raw.npy', thresh_raw)
np.save(f'{cache}/clim_raw.npy', clim_raw)

def circ_smooth(a):  # (367, NC); a[0] unused; days 1..366 wrap modulo 366
    a366 = a[1:]
    out = np.zeros_like(a366)
    for k in range(-15, 16):
        out += np.roll(a366, -k, axis=0)
    out /= 31.0
    res = np.full_like(a, np.nan)
    res[1:] = out
    return res

thresh_s = circ_smooth(thresh_raw)
clim_s   = circ_smooth(clim_raw)
np.save(f'{cache}/thresh_s.npy', thresh_s)
np.save(f'{cache}/clim_s.npy', clim_s)
print('saved. elapsed', round(time.time()-t0, 2), 's')

# verification vs brute force (sane tolerance)
rng = np.random.default_rng(0)
maxdiff = 0.0
for _ in range(12):
    d = int(rng.integers(1, 367)); c = int(rng.integers(0, NC))
    rows = np.array([(d + k - 1) % 366 for k in range(-15, 16)])  # rows of a[1:]
    bf_t = thresh_raw[1:][rows, c].mean()
    bf_c = clim_raw[1:][rows, c].mean()
    maxdiff = max(maxdiff, abs(bf_t - thresh_s[d, c]), abs(bf_c - clim_s[d, c]))
print('max |smooth - bruteforce| over 24 checks:', maxdiff)
assert maxdiff < 1e-9
print('wrap smoothing verified')

sea_finite = np.isfinite(tgt).all(axis=0)
print('sea cells (finite all target days):', int(sea_finite.sum()), 'of', NC)
ii, jj = np.where(sea_finite)
c0 = (int(ii[len(ii)//2]), int(jj[len(jj)//2]))
ci = c0[0]*60 + c0[1]
print('sample sea cell (row,col):', c0)
print('raw thresh doy 153..244/13:', np.round(thresh_raw[153:245:13, ci], 3))
print('sm  thresh doy 153..244/13:', np.round(thresh_s[153:245:13, ci], 3))
print('raw clim  doy 153..244/13:', np.round(clim_raw[153:245:13, ci], 3))
print('sm  clim  doy 153..244/13:', np.round(clim_s[153:245:13, ci], 3))
print('NaN check thresh_s:', bool(np.isnan(thresh_s[1:]).any()), '| clim_s:', bool(np.isnan(clim_s[1:]).any()))