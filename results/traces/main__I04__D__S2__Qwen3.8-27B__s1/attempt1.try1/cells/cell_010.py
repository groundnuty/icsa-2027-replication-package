import xarray as xr, numpy as np, json, math
from datetime import date, timedelta

# --- independent reimplementation (pure python, no pandas/numpy percentiles) ---
def fixed_doy(dt):  # 366-day calendar
    base = date(2000, 1, 1)
    return (dt.replace(year=2000) - base).days + 1

def is_leap(y): return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)

def hazen90(vals):
    x = np.sort(np.asarray([v for v in vals if math.isfinite(v)], dtype=np.float64))
    n = x.size
    if n == 0: return math.nan
    h = n * 0.9 + 0.5          # 1-indexed hazen position
    lo = int(math.floor(h)); 
    if lo >= n: return x[-1]
    frac = h - lo
    return x[lo-1] + frac * (x[lo] - x[lo-1])

def pool_dates(d, baseline=(date(1992,1,1), date(2002,12,31))):
    out = set()
    if d == 60: return out
    d0, d1 = baseline
    y = d0.year
    while date(y,1,1) <= d1:
        # find the calendar date in year y with fixed doy d
        cand = date(2000,1,1) + timedelta(days=d-1)
        dt = date(y, cand.month, cand.day) if (is_leap(y) or cand.month < 3 or d < 60) else None
        if dt is not None and d0 <= dt <= d1 and fixed_doy(dt) == d:
            for k in range(-5, 6):
                out.add(dt + timedelta(days=k))
        y += 1
    return out

# load source + outputs
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lat, lon = ds.latitude.values, ds.longitude.values
lats = np.where((lat>=54.39)&(lat<=55.59))[0]
lons = np.where((lon>=18.25)&(lon<=19.45))[0]
def gidx(s):
    i = int(np.searchsorted(t, np.datetime64(s))); assert t[i]==np.datetime64(s); return i
iL0, iL1 = gidx('1991-12-27'), gidx('2020-08-31')
S = ds.analysed_sst.isel(time=slice(iL0,iL1+1), latitude=lats, longitude=lons).values.astype(np.float64)
dates = [date(1991,12,27) + timedelta(days=i) for i in range(S.shape[0])]
d2i = {d:i for i,d in enumerate(dates)}
C = 3600
tt0, tt1 = gidx('2020-06-01')-iL0, gidx('2020-08-31')-iL0
tt = S[tt0:tt1+1].reshape(92, C)
finite = np.isfinite(tt).all(axis=0)
print('recomputed sea cells:', int(finite.sum()))

out = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print('mask:', out, end='\n\n')
m = out['mhw'].values
print('mask shape', m.shape, m.dtype, 'sum', int(m.sum()))
print('time', out.time.values[0], '->', out.time.values[-1], 'lat', out.latitude.values[0], '->', out.latitude.values[-1], 'lon', out.longitude.values[0], '->', out.longitude.values[-1])
print('land cells all zero:', bool((m[:, ~finite.reshape(60,60)].ravel() == 0).all()))

# per-doy smoothed threshold for a cell, independent
def smoothed_thr_cell(c):
    thr = {}
    for d in range(1, 367):
        if d == 60:
            continue
        idxs = [d2i[dd] for dd in pool_dates(d)]
        vals = [S[i, c//60, c%60] for i in idxs]
        thr[d] = hazen90(vals)
    thr[60] = 0.5*(thr[59]+thr[61])
    return {d: np.mean([thr[(d-1+k) % 366 + 1] for k in range(-15,16)]) for d in range(1,367)}

def cell_mhw(c):
    sthr = smoothed_thr_cell(c)
    hot = np.zeros(92, dtype=bool)
    for k in range(92):
        dt = date(2020,6,1) + timedelta(days=k)
        d = fixed_doy(dt)
        v = tt[k, c]
        hot[k] = math.isfinite(v) and v >= sthr[d]
    dh = np.diff(np.concatenate([[0], hot.astype(int), [0]]))
    s_ = np.flatnonzero(dh==1); e_ = np.flatnonzero(dh==-1)-1
    segs = [[a,b] for a,b in zip(s_,e_) if b-a+1 >= 5]
    merged = []
    for seg in segs:
        if merged and seg[0]-merged[-1][1]-1 <= 2: merged[-1][1] = seg[1]
        else: merged.append(seg)
    res = np.zeros(92, dtype=bool)
    for a,b in merged: res[a:b+1] = True
    return res

rng = np.random.default_rng(7)
sample = list(rng.choice(np.flatnonzero(finite), 5, replace=False)) + [int(np.flatnonzero(finite)[0]), int(np.flatnonzero(finite)[-1])]
print('sample cells:', sample)
maxdiff = 0.0
for c in sample:
    exp = cell_mhw(c).astype(np.uint8)
    got = m[:, c//60, c%60]
    bad = np.flatnonzero(exp != got)
    print('cell', c, 'mismatch days:', bad.tolist())
# compare thresholds numerically for one cell
c = sample[0]
sthr = smoothed_thr_cell(c)
for d in (153, 198, 244):
    # reconstruct smoothed thr from output? we didn't save it; instead verify hazen on raw pool
    idxs = [d2i[dd] for dd in pool_dates(d)]
    print('cell', c, 'doy', d, 'indep hazen thr', round(sthr[d], 6), 'pool n', len([v for v in (S[i, c//60, c%60] for i in idxs) if math.isfinite(v)]))

# events from mask file
act = m.any(axis=1)
dha = np.diff(np.concatenate([[0], act.astype(int), [0]]))
sa = np.flatnonzero(dha==1); ea = np.flatnonzero(dha==-1)-1
ev = [(str(out.time.values[s].astype('datetime64[D]')), str(out.time.values[e].astype('datetime64[D]'))) for s,e in zip(sa,ea)]
print('events from mask file:', ev)
rep = json.load(open('/work/output/report.json'))
print('events in report   :', [(e['onset'], e['end']) for e in rep['events']])
print('match:', ev == [(e['onset'], e['end']) for e in rep['events']])
print('mhw-day total from file:', int(m.sum()))
