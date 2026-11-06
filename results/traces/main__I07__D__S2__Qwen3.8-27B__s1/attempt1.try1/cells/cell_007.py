import xarray as xr, numpy as np, pickle
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
li = np.arange(48, 108); lo = np.arange(353, 413)
t = ds.indexes['time']; tdates = np.array(t.date)
def tidx(d): return int(np.searchsorted(tdates, np.datetime64(d)))
b0, b1 = tidx('1991-12-27'), tidx('2003-01-05')
t0, t1 = tidx('2021-06-01'), tidx('2021-08-31')
base = ds['analysed_sst'].isel(time=slice(b0,b1+1), latitude=li, longitude=lo).values.astype(np.float64)
tgt  = ds['analysed_sst'].isel(time=slice(t0,t1+1),  latitude=li, longitude=lo).values.astype(np.float64)
base_dates = tdates[b0:b1+1]; tgt_dates = tdates[t0:t1+1]

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_leap(a):
    s = pd.Series(a.astype('datetime64[ns]'))
    return CUM[s.dt.month.to_numpy()-1] + s.dt.day.to_numpy()
base_doy = doy_leap(base_dates); tgt_doy = doy_leap(tgt_dates)

# spatial pattern of sea cells
sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', sea.sum(), '/', sea.size)
coarse = sea.reshape(12,5,12,5).all(axis=(1,3))
for r in coarse: print(''.join('#' if v else '.' for v in r))

# NaN baseline-pool pattern per day
bl_mask = (base_dates >= np.datetime64('1992-01-01')) & (base_dates <= np.datetime64('2002-12-31'))
bl_idx = np.where(bl_mask)[0]; bl_doy = base_doy[bl_idx]
pools = {}
for d in range(1, 367):
    if d == 60: continue
    ibs = bl_idx[bl_doy == d]
    pools[d] = np.concatenate([np.arange(ib-5, ib+6) for ib in ibs])

# manual hazen quantile check on a sample pool
def hazen_manual(v, q=0.9):
    v = np.sort(v[np.isfinite(v)])
    n = len(v)
    if n == 0: return np.nan
    if n == 1: return v[0]
    pos = 1 + q*(n-1)
    lo = int(np.floor(pos)); site_g = pos - lo
    return v[lo-1] + (v[lo] - v[lo-1])*site_g if lo < n else v[-1]

i, j = 10, 10
for d in (153, 200, 244):
    P = base[pools[d]][:, i, j]
    a = hazen_manual(P); b = np.nanquantile(P, 0.9, method='hazen')
    print(f'd={d} cell(10,10): manual={a:.6f} numpy={b:.6f} match={np.isclose(a,b)}')
print('baseline pool finite fraction cell(10,10):', np.isfinite(base[pools[200]][:,10,10]).mean())

# find sea cells with NaN smoothed threshold in target doys (need thr first) - compute quickly
N = 3600
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d, idx in pools.items():
        P2 = base[idx].reshape(len(idx), N)
        thr[d-1] = np.nanquantile(P2, 0.9, method='hazen', axis=0).reshape(60,60)
        clim[d-1] = np.nanmean(P2, axis=0).reshape(60,60)
thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
idx31 = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
thr_s = np.take(thr, idx31, axis=0).mean(axis=1)
clim_s = np.take(clim, idx31, axis=0).mean(axis=1)

nan_thr_tgt = np.isnan(thr_s[tgt_doy-1]).any(axis=0)
print('sea cells w/ NaN smoothed thr in target:', int((nan_thr_tgt & sea).sum()))
print('non-sea cells w/ NaN smoothed thr in target:', int((nan_thr_tgt & ~sea).sum()))
print('sea cells w/ finite thr:', int((~nan_thr_tgt & sea).sum()))

# which target days are affected and for how many cells
cnt = np.isnan(thr_s[tgt_doy-1]).sum(axis=0)
print('NaN thr counts per target day (max):', cnt.max(), 'on', str(tgt_dates[cnt.argmax()]))

# check overlap: are the NaN-thr sea cells the same cells that are non-sea? overlap already shown.
# where are the NaN-thr sea cells?
ys, xs = np.where(nan_thr_tgt & sea)
print('NaN-thr sea cells count', len(ys), 'lat idx', ys.min() if len(ys) else '-', ys.max() if len(ys) else '-')

# manual smoothing check for one cell
c_thr = thr[:, 20, 30]
manual = np.array([c_thr[(d-15-15-1+366*0 if False else (d - 15) % 366 - 1) ] if False else np.mean(c_thr[[(d-15+k) % 366 for k in range(31)]]) for d in range(1, 367)])
# careful: day d (1-based) averages days d-15..d+15 mod 366 (1-based) -> 0-based indices (d-16+k)%366
manual = np.array([np.mean(c_thr[[(d-16+k) % 366 for k in range(31)]]) for d in range(1, 367)])
print('smooth max abs diff:', np.abs(manual - thr_s[:,20,30]).max())

with open('/work/state.pkl','wb') as f:
    pickle.dump({'thr_s':thr_s,'clim_s':clim_s,'sea':sea,'pools':None}, f)
print('ok')
