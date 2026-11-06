import xarray as xr, numpy as np, json, math
from datetime import date, timedelta

def fixed_doy(dt):
    return (dt.replace(year=2000) - date(2000,1,1)).days + 1
def is_leap(y): return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)

def hazen90(vals):
    x = np.sort(np.asarray([v for v in vals if math.isfinite(v)], dtype=np.float64))
    n = x.size
    if n == 0: return math.nan
    h = n * 0.9 + 0.5
    lo = int(math.floor(h))
    if lo >= n: return x[-1]
    frac = h - lo
    return x[lo-1] + frac * (x[lo] - x[lo-1])

def pool_dates(d):
    out = set()
    if d == 60: return out
    d0, d1 = date(1992,1,1), date(2002,12,31)
    cand = date(2000,1,1) + timedelta(days=d-1)
    for y in range(1992, 2003):
        if is_leap(y) or d != 60:
            try:
                dt = date(y, cand.month, cand.day)
            except ValueError:
                continue
            if d0 <= dt <= d1 and fixed_doy(dt) == d:
                for k in range(-5, 6):
                    out.add(dt + timedelta(days=k))
    return out

# sanity: pool sizes and spans
ps = {d: pool_dates(d) for d in range(1,367)}
print('pool sizes (d59,d61,d62,d153,d366):', len(ps[59]), len(ps[61]), len(ps[62]), len(ps[153]), len(ps[366]))
alld = [dd for s in ps.values() for dd in s]
print('pool span:', min(alld), max(alld), 'feb29-92 in ps[59]:', date(1992,2,29) in ps[59], 'feb29-92 in ps[61]:', date(1992,2,29) in ps[61], 'feb29 in ps[60]:', date(1992,2,29) in ps[60])

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
tt0, tt1 = gidx('2020-06-01')-iL0, gidx('2020-08-31')-iL0
tt = S[tt0:tt1+1].reshape(92, 3600)
finite = np.isfinite(tt).all(axis=0)

out = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
m = out['mhw'].values
print('land cells all zero:', bool((m[:, ~finite.reshape(60,60)].ravel() == 0).all()))

def smoothed_thr_cell(c):
    thr = {}
    for d in range(1, 367):
        if d != 60:
            idxs = [d2i[dd] for dd in ps[d]]
            thr[d] = hazen90([S[i, c//60, c%60] for i in idxs])
    thr[60] = 0.5*(thr[59]+thr[61])
    return {d: np.mean([thr[((d-1+k) % 366) + 1] for k in range(-15,16)]) for d in range(1,367)}

def cell_mhw(c):
    sthr = smoothed_thr_cell(c)
    hot = np.zeros(92, dtype=bool)
    for k in range(92):
        dt = date(2020,6,1) + timedelta(days=k)
        v = tt[k, c]
        hot[k] = math.isfinite(v) and v >= sthr[fixed_doy(dt)]
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
allok = True
for c in sample:
    exp = cell_mhw(c).astype(np.uint8)
    got = m[:, c//60, c%60]
    bad = np.flatnonzero(exp != got)
    if bad.size: allok = False
    print('cell', c, 'mismatches:', bad.tolist())
print('ALL SAMPLED CELLS MATCH:', allok)

act = m.any(axis=(1,2))
dha = np.diff(np.concatenate([[0], act.astype(int), [0]]))
sa = np.flatnonzero(dha==1); ea = np.flatnonzero(dha==-1)-1
ev = [(str(out.time.values[s].astype('datetime64[D]')), str(out.time.values[e].astype('datetime64[D]'))) for s,e in zip(sa,ea)]
rep = json.load(open('/work/output/report.json'))
print('events from mask file:', ev)
print('match report:', ev == [(e['onset'], e['end']) for e in rep['events']])
print('mhw-day total:', int(m.sum()), 'active days:', int(act.sum()))
print('report keys ok:', set(rep) == {'region','baseline_analysed','target_analysed','events','complete','caveats'})
