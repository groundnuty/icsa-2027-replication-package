import numpy as np

z = np.load('/work/thr_clim.npz')
thr, clim, thr_s, clim_s = z['thr'], z['clim'], z['thr_s'], z['clim_s']

# 1) verify wrap-around smoothing numerically for random doys/cells
rng = np.random.default_rng(1)
ok = True
for _ in range(200):
    d = rng.integers(0, 366); i = rng.integers(0, 60); j = rng.integers(0, 60)
    idxs = [(d + k) % 366 for k in range(-15, 16)]
    manual = thr[idxs, i, j].mean()
    if abs(manual - thr_s[d, i, j]) > 1e-9: ok = False
print('smoothing wrap check OK:', ok)
# also clim
ok = True
for _ in range(200):
    d = rng.integers(0, 366); i = rng.integers(0, 60); j = rng.integers(0, 60)
    idxs = [(d + k) % 366 for k in range(-15, 16)]
    if abs(clim[idxs, i, j].mean() - clim_s[d, i, j]) > 1e-9: ok = False
print('clim smoothing wrap check OK:', ok)

# 2) day-60 fill check (pre-smoothing): thr[59] == mean(thr[58], thr[60])
print('day60 pre-smooth fill OK (thr):', np.allclose(thr[59], 0.5*(thr[58]+thr[60])), '(clim):', np.allclose(clim[59], 0.5*(clim[58]+clim[60])))

# 3) brute-force per-cell MHW check on sample cells from raw masks
m = np.load('/work/mhw_state.npz', allow_pickle=True)
mhw = m['mhw']; sea = m['sea']
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
idx = np.load('/work/idx.npz'); j0, j1 = int(idx['j0']), int(idx['j1'])
lat_idx = np.where((ds.latitude.values >= 56.09) & (ds.latitude.values <= 57.29))[0]
lon_idx = np.where((ds.longitude.values >= 10.55) & (ds.longitude.values <= 11.75))[0]
sst = ds.analysed_sst.isel(time=slice(j0, j1), latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(dates):
    months = dates.astype('datetime64[M]')
    mth = (months - months.astype('datetime64[Y]')).astype(int)
    return cum[mth] + ((dates - months).astype(int) + 1)
doy_t = doy_of(ds.time.values[j0:j1].astype('datetime64[D]')) - 1

def brute(h):
    # returns mhw mask via explicit loop semantics: runs>=5 then join gaps<=2
    n = len(h); runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]: j += 1
            if j - i + 1 >= 5: runs.append([i, j])
            i = j + 1
        else:
            i += 1
    out = np.zeros(n, bool)
    if not runs: return out
    ms, me = [runs[0][0]], [runs[0][1]]
    for s, e in runs[1:]:
        if s - me[-1] - 1 <= 2: me[-1] = e
        else: ms.append(s); me.append(e)
    for s, e in zip(ms, me): out[s:e+1] = True
    return out

cells = [(30,30),(0,0),(59,59),(29,29),(10,25),(45,50),(5,55),(55,5)]
okall = True
for (i, j) in cells:
    if not sea[i, j]:
        print('cell', (i,j), 'is land, mhw all zero:', not mhw[:, i, j].any()); continue
    h = sst[:, i, j] >= thr_s[doy_t, i, j]
    b = brute(h)
    if not np.array_equal(b, mhw[:, i, j]): okall = False; print('MISMATCH cell', (i,j))
print('brute-force MHW check on sample cells OK:', okall)

# 4) per-cell stats
nruns_per_cell = (np.diff(mhw.astype(np.int8), axis=0) == 1).sum(axis=0) + (mhw[0] & sea)
print('cells with >1 per-cell MHW:', int((nruns_per_cell > 1).sum()))
durs = mhw.sum(axis=0)
print('per-cell MHW length stats: min', int(durs[sea].min()), 'median', float(np.median(durs[sea])), 'max', int(durs[sea].max()))
onsets = mhw.argmax(axis=0)
import collections
print('onset day distribution (first 10 most common):', collections.Counter(onsets[sea]).most_common(10))
ends = nt = mhw.shape[0]
lastd = mhw.shape[0] - 1 - mhw[::-1].argmax(axis=0)
print('end day distribution (first 10):', collections.Counter(lastd[sea]).most_common(10))
print('sea cells where no MHW:', int((~mhw.any(axis=0) & sea).sum()))