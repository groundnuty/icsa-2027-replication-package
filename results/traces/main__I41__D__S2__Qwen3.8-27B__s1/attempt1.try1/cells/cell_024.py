v2 = r'''
import numpy as np, xarray as xr, json

thr_s  = np.load('/work/p_thr_s.npy')
clim_s = np.load('/work/p_clim_s.npy')
p_mask = np.load('/work/p_mask.npy')
p_sea  = np.load('/work/p_sea.npy')
p_events = json.load(open('/work/p_events.json'))['events']

thr2s = np.load('/work/thr2s.npy')
Xt    = np.load('/work/Xt.npy')
tdoy  = np.load('/work/tdoy.npy')
sea   = np.load('/work/sea.npy')
assert sea.shape == (3600,)

# 1) threshold arrays: pipeline (nanquantile hazen) vs independent
d = np.abs(thr_s - thr2s)
d = d[np.isfinite(d)]
print("thr max diff:", d.max(), " n_finite:", d.size, " equal:", np.array_equal(thr_s, thr2s))
print("sea equal:", np.array_equal(sea, p_sea), " sea count:", int(sea.sum()))

# 2) independent MHW detection: label-based
from scipy import ndimage
hot = Xt >= thr2s[tdoy, :]
mask2 = np.zeros_like(p_mask)
for c in range(p_mask.shape[1]):
    if not sea[c]:
        continue
    h = hot[:, c]
    # label hot runs
    lab, n = ndimage.label(h)
    runs = []
    for k in range(1, n+1):
        idx = np.where(lab == k)[0]
        if len(idx) >= 5:
            runs.append([idx[0], idx[-1]])
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    for s, e in merged:
        mask2[s:e+1, c] = 1
print("mask equal:", np.array_equal(mask2, p_mask), " diff cells:", int((mask2 != p_mask).sum()))

# 3) regional events
active = mask2.any(axis=1)
lab2, n2 = ndimage.label(active)
events2 = []
for k in range(1, n2+1):
    idx = np.where(lab2 == k)[0]
    events2.append((str(idx[0]), str(idx[-1])))
tdays = [str(x) for x in (np.datetime64('2021-06-01') + np.arange(92, dtype='int64')*np.timedelta64(1,'D'))]
events2 = [(tdays[s], tdays[e]) for s, e in events2]
print("events pipeline:", p_events)
print("events  indep  :", events2)
print("events equal:", events2 == p_events)

# 4) output files
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw']
assert m.dtype == np.uint8, m.dtype
assert tuple(m.dims) == ('time', 'lat', 'lon'), m.dims
assert m.shape == (92, 60, 60)
mref = p_mask.reshape(92, 60, 60)
print("netcdf values equal:", bool((m.values == mref).all()))
print("time:", m.time.values[0], "...", m.time.values[-1])
print("lat range:", float(m.lat.values.min()), float(m.lat.values.max()))
print("lon range:", float(m.lon.values.min()), float(m.lon.values.max()))
# land cells zero: map sea mask to (lat, lon) grid
latm = (np.array([float(v) for v in m.lat.values]) >= 61.57 - 1e-5) & (np.array([float(v) for v in m.lat.values]) <= 62.77 + 1e-5)
lonm = (np.array([float(v) for v in m.lon.values]) >= 20.17 - 1e-5) & (np.array([float(v) for v in m.lon.values]) <= 21.37 + 1e-5)
print("all region cells present:", latm.all() and lonm.all(), latm.sum(), lonm.sum())
sea_grid = sea.reshape(60, 60)
land = ~sea_grid
print("land cell days non-zero in netcdf:", int((m.values[:, land[0], land[1]].sum()) if land.any() else 0))
# check every target day present
import datetime
expect = np.datetime64('2021-06-01') + np.arange(92, dtype='int64')*np.timedelta64(1,'D')
print("time axis ok:", bool((m.time.values.astype('datetime64[D]') == expect).all()))

rep = json.load(open('/work/output/report.json'))
print(json.dumps(rep, indent=1)[:900])
print("report keys:", sorted(rep.keys()))
print("VERIFY2 DONE")
'''
open('/work/verify2.py','w').write(v2)
exec(open('/work/verify2.py').read())
