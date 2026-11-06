import fsspec, xarray as xr, numpy as np, json, os, time, warnings
from datetime import date, timedelta
warnings.filterwarnings('ignore')
t_start = time.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']; t = ds['time'].values
lat = ds['latitude'].values; lon = ds['longitude'].values
li = np.where((lat.astype(np.float64)>=54.17)&(lat.astype(np.float64)<=55.37))[0]
lo = np.where((lon.astype(np.float64)>=13.25)&(lon.astype(np.float64)<=14.45))[0]
print('region cells:', len(li), len(lo), '->', len(li)*len(lo))

# --- load slices ---
b0 = np.searchsorted(t, np.datetime64('1991-12-27')); b1 = np.searchsorted(t, np.datetime64('2003-01-05'))
tb0 = np.searchsorted(t, np.datetime64('2014-06-01')); tb1 = np.searchsorted(t, np.datetime64('2014-08-31'))
t0=time.time()
B = v.isel(time=slice(b0,b1+1), latitude=li, longitude=lo).values.astype(np.float64)
print('baseline loaded', B.shape, 'in', time.time()-t0, 's; range', t[b0], '->', t[b1])
t0=time.time()
T = v.isel(time=slice(tb0,tb1+1), latitude=li, longitude=lo).values.astype(np.float64)
print('target loaded', T.shape, 'in', time.time()-t0, 's; range', t[tb0], '->', t[tb1])

nlat, nlon = len(li), len(lo)
Bf = B.reshape(B.shape[0], nlat*nlon)   # (4028, 3600)
Tf = T.reshape(T.shape[0], nlat*nlon)   # (92, 3600)

# --- sea cells ---
sea = np.all(np.isfinite(Tf), axis=0)
print('sea cells:', sea.sum(), 'of', Tf.shape[1])

# --- doy mapping (leap-based) ---
leap = date(2000,1,1)
doy2cal = {}
for d in range(1,367):
    dd = leap + timedelta(days=d-1)
    doy2cal[d] = (dd.month, dd.day)
cal2doy = {(m,d): i for i,(m,d) in doy2cal.items()}
t_bdates = [date(1991,12,27)+timedelta(days=k) for k in range(Bf.shape[0])]
pos = {d: i for i,d in enumerate(t_bdates)}
t_tdates = [date(2014,6,1)+timedelta(days=k) for k in range(Tf.shape[0])]
t_doy = [cal2doy[(d.month, d.day)] for d in t_tdates]
print('target doy first/last:', t_doy[0], t_doy[-1])

years = list(range(1992,2003))
isleap = lambda y: (y%4==0)
# build row index lists per doy
rows_by_d = {}
for d in range(1,367):
    if d == 60: continue
    ys = [y for y in years if (d <= 59 or d == 61 or isleap(y) or True) if not (d==366 and not isleap(y))]
    if d == 60: ys = []
    rows = []
    for y in ys:
        m, day = doy2cal[d]
        anchor = date(y, m, day)
        assert anchor in pos, (d, y, anchor)
        i = pos[anchor]
        rows.extend(range(i-5, i+6))
    rows_by_d[d] = np.array(rows)
print('pool sizes: d=1:', len(rows_by_d[1]), 'd=366:', len(rows_by_d[366]), 'd=59:', len(rows_by_d[59]))

# --- threshold & climatology per cell ---
NC = Tf.shape[1]
thr = np.full((366, NC), np.nan); clim = np.full((366, NC), np.nan)
t0=time.time()
for d in range(1,367):
    if d == 60: continue
    pool = Bf[rows_by_d[d]]          # (Nd, 3600)
    thr[d-1] = np.nanquantile(pool, 0.9, method='hazen', axis=0)
    clim[d-1] = np.nanmean(pool, axis=0)
thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
print('pools done in', time.time()-t0, 's')
raw_nan_thr = np.isnan(thr)
print('raw thr NaN (sea cells):', int(raw_nan_thr[:, sea].sum()))

# --- smoothing: 31-day centred wrap mean ---
IDX = (np.arange(366)[:,None] - 15 + np.arange(31)[None,:]) % 366
t0=time.time()
thr_s = thr[IDX].mean(axis=1)
clim_s = clim[IDX].mean(axis=1)
print('smooth done in', time.time()-t0, 's')
print('smoothed thr NaN (sea cells):', int(np.isnan(thr_s)[:, sea].sum()), 'clim:', int(np.isnan(clim_s)[:, sea].sum()))

# --- per-cell MHW over target ---
hot = Tf >= thr_s[t_doy]   # (92, 3600); NaN thr -> False
print('hot days total (all cells):', int(hot.sum()))
cellmhw = np.zeros(Tf.shape, dtype=bool)
npre = np.zeros(NC, int); npost = np.zeros(NC, int)
for c in range(NC):
    h = hot[:, c]
    p = np.concatenate(([False], h, [False]))
    d1 = np.diff(p.astype(np.int8))
    s = np.where(d1==1)[0]; e = np.where(d1==-1)[0]-1
    runs = [(s_, e_) for s_, e_ in zip(s, e) if e_-s_+1 >= 5]
    npre[c] = len(runs)
    merged = []
    for s_, e_ in runs:
        if merged and s_ - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e_)
        else:
            merged.append((s_, e_))
    npost[c] = len(merged)
    for s_, e_ in merged:
        cellmhw[s_:e_+1, c] = True
print('per-cell MHWs pre-merge:', int(npre.sum()), 'post-merge:', int(npost.sum()))
active = cellmhw.any(axis=1)
print('active days:', int(active.sum()), 'of', len(active))
pa = np.concatenate(([False], active, [False])); da = np.diff(pa.astype(np.int8))
es = np.where(da==1)[0]; ee = np.where(da==-1)[0]-1
events = [(str(t_tdates[s_].isoformat()), str(t_tdates[e_].isoformat())) for s_, e_ in zip(es, ee)]
print('events:', json.dumps(events))

# save intermediates for verification call
np.savez_compressed('/tmp/mhw_state.npz', cellmhw=cellmhw, active=active, thr_s=thr_s, clim_s=clim_s,
                    hot=hot, sea=sea, Bf=Bf, Tf=Tf, doy=t_doy)
print('total', time.time()-t_start)
with open('/tmp/events.json','w') as fh: json.dump(events, fh)
ds.close(); f.close()
