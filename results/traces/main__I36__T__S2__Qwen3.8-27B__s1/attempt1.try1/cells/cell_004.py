import fsspec, numpy as np, xarray as xr, json, os, warnings
from datetime import date

fs = fsspec.filesystem('onedata')
PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(PATH, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

latv = ds.latitude.values.astype(np.float64)
lonv = ds.longitude.values.astype(np.float64)
mlat = (latv>=60.09)&(latv<=61.29)
mlon = (lonv>=20.01)&(lonv<=21.21)
lat_sel = ds.latitude[mlat].values
lon_sel = ds.longitude[mlon].values
LA, LO = int(mlat.sum()), int(mlon.sum())

t = ds.time.values
mt = (t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-08-31'))
dts = t[mt].astype('datetime64[D]').astype(object)
T = len(dts)
ord_ = np.array([d.toordinal() for d in dts])

sub = ds.analysed_sst.isel(time=mt, latitude=mlat, longitude=mlon).values.astype(np.float64)

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
mm = np.array([d.month for d in dts]); dd = np.array([d.day for d in dts])
doy = cum[mm-1] + dd
print('doy 2000-02-29 =', doy[np.flatnonzero(ord_==date(2000,2,29).toordinal())[0]])
print('doy 2003-03-01 =', doy[np.flatnonzero(ord_==date(2003,3,1).toordinal())[0]])
print('doy 1993-12-31 =', doy[np.flatnonzero(ord_==date(1993,12,31).toordinal())[0]])

inb = (ord_ >= date(1992,1,1).toordinal()) & (ord_ <= date(2002,12,31).toordinal())
C = LA*LO
thr = np.full((366, C), np.nan); clim = np.full((366, C), np.nan)
used = np.zeros(T, bool)
psizes = {}
for d in range(1, 367):
    if d == 60: continue
    bm = (doy==d) & inb
    pm = np.zeros(T, bool)
    for k in range(-5, 6):
        if k >= 0: pm[k:] |= bm[:T-k]
        else:      pm[:T+k] |= bm[-k:]
    psizes[int(pm.sum())] = psizes.get(int(pm.sum()), 0) + 1
    used |= pm
    pool = sub[pm]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        thr[d] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim[d] = np.nanmean(pool, axis=0)
print('pool sizes per doy:', psizes)
thr[60]  = (thr[59]  + thr[61])  / 2.0
clim[60] = (clim[59] + clim[61]) / 2.0

offs = np.arange(-15, 16)
def smooth31(a):
    out = np.empty_like(a)
    for d in range(366):
        out[d] = a[(d+offs)%366].mean(axis=0)
    return out
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print('thr_s nan count', int(np.isnan(thr_s).sum()))

tm = (ord_ >= date(2003,6,1).toordinal()) & (ord_ <= date(2003,8,31).toordinal())
Tt = int(tm.sum())
dts_t = dts[tm]
print('target days', Tt, dts_t[0], dts_t[-1])
doy_t = doy[tm]
sst_t = sub[tm]
sea = np.isfinite(sst_t).all(axis=0)
print('sea cells', int(sea.sum()), 'of', C)

thr_t = thr_s[doy_t]
seaf = sea.ravel()
flat = sst_t.reshape(Tt, -1)
thf = thr_t.reshape(Tt, -1)
hot = np.zeros((Tt, C), bool)
hot[:, seaf] = flat[:, seaf] >= thf[:, seaf]

mhw_c = np.zeros((Tt, C), bool)
for j in np.flatnonzero(seaf):
    h = hot[:, j]
    pad = np.concatenate(([0], h.view(np.uint8), [0]))
    diff = np.diff(pad.astype(np.int8))
    st = np.flatnonzero(diff==1); en = np.flatnonzero(diff==-1)-1
    runs = [(s,e) for s,e in zip(st,en) if e-s+1>=5]
    merged=[]
    for s,e in runs:
        if merged and (s - merged[-1][1] - 1) <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    for s,e in merged:
        mhw_c[s:e+1, j] = True

mhw = mhw_c.reshape(Tt, LA, LO).astype(np.uint8)
active = mhw_c.any(axis=1)
pad = np.concatenate(([False], active, [False]))
dif = np.diff(pad.astype(np.int8))
st = np.flatnonzero(dif==1); en = np.flatnonzero(dif==-1)-1
events=[]
for s,e in zip(st,en):
    events.append((dts_t[s].isoformat(), dts_t[e].isoformat(), e-s+1))
print('events:', events)
print('active days total', int(active.sum()))

c = C//2
idx_day = list(dts_t).index(date(2003,7,20))
r, cc = divmod(c, LO)
print('diag cell', c, 'lat', latv[mlat][r], 'lon', lonv[mlon][cc])
print('2003-07-20 sst', flat[idx_day, c], 'thr', thf[idx_day, c])
ub = dts[used]
print('baseline used:', min(ub), max(ub), 'n used days', int(used.sum()))
tg_doy_nan = int(np.isnan(thr_s[doy_t][:, seaf]).sum())
print('NaN smoothed thr among sea cells x target days:', tg_doy_nan)
print('hot days total (sea cells):', int(hot[:, seaf].sum()), 'of', int(seaf.sum())*Tt)

import pickle
with open('/tmp/stash.pkl','wb') as fh:
    pickle.dump(dict(lat_sel=lat_sel, lon_sel=lon_sel, dts_t=dts_t, mhw=mhw, events=events,
                     used_min=min(ub).isoformat(), used_max=max(ub).isoformat(),
                     target_min=dts_t[0].isoformat(), target_max=dts_t[-1].isoformat(),
                     nsea=int(sea.sum()), Tt=Tt), fh)
ds.close(); f.close()
print('DONE')
