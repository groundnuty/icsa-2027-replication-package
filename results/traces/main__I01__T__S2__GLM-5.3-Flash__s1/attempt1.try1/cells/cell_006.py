import fsspec, xarray as xr, numpy as np, datetime as dt, warnings, time

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds['analysed_sst']; tvals = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
la = np.where((lat>=54.13)&(lat<=55.33))[0]; lo = np.where((lon>=14.67)&(lon<=15.87))[0]
b0 = int(np.searchsorted(tvals, np.datetime64('1991-12-27')))
b1 = int(np.searchsorted(tvals, np.datetime64('2003-01-05'), 'right'))
base_D = tvals[b0].astype('datetime64[D]')

t0=time.time()
basel = sst.isel(time=slice(b0,b1), latitude=slice(la[0],la[-1]+1), longitude=slice(lo[0],lo[-1]+1)).values.astype(np.float64)
print("baseline re-read %.1fs" % (time.time()-t0))

# manual Hazen (type 5) quantile
def hazen_q(x, p=0.9):
    x = np.sort(x[~np.isnan(x)])
    n = x.size
    if n == 0: return np.nan
    pos = n*p + 0.5 - 1.0
    if pos <= 0: return float(x[0])
    if pos >= n-1: return float(x[-1])
    l = int(np.floor(pos)); w = pos - l
    return (1-w)*float(x[l]) + w*float(x[l+1])

# validate manual vs numpy on random pools
rng = np.random.default_rng(0)
ok = True
for _ in range(200):
    n = rng.integers(1, 300)
    x = rng.normal(size=int(n))
    if n <= 2: continue
    a = hazen_q(x); b = np.quantile(x, 0.9, method='hazen')
    if not np.isclose(a, b, rtol=0, atol=1e-12): ok=False; print("MISMATCH", n, a, b)
print("manual hazen == numpy 'hazen':", ok)

years = list(range(1992,2003))
def center_k(y,d):
    if d<=59: c = dt.date(y,1,1)+dt.timedelta(days=d-1)
    elif d>=61: c = dt.date(y,3,1)+dt.timedelta(days=d-61)
    else: return None
    return int((np.datetime64(c,'D')-base_D).astype(int))

t0=time.time()
thr_raw = np.full((366,60,60), np.nan); clim_raw = np.full((366,60,60), np.nan)
for d in range(1,367):
    if d==60: continue
    ks=[]
    for y in years:
        k = center_k(y,d)
        ks.extend(range(k-5,k+6))
    ks = np.array(sorted(set(ks)))
    pool = basel[ks].reshape(len(ks), -1)
    q = np.empty(pool.shape[1]); m = np.empty(pool.shape[1])
    for j in range(pool.shape[1]):
        col = pool[:,j]
        q[j] = hazen_q(col)
        cc = col[np.isfinite(col)]
        m[j] = cc.mean() if cc.size else np.nan
    thr_raw[d-1] = q.reshape(60,60); clim_raw[d-1] = m.reshape(60,60)
print("manual pool loop %.1fs" % (time.time()-t0))

thr_raw[59] = 0.5*(thr_raw[58]+thr_raw[60]); clim_raw[59] = 0.5*(clim_raw[58]+clim_raw[60])
sidx = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
thr_sm2 = thr_raw[sidx].mean(axis=1); clim_sm2 = clim_raw[sidx].mean(axis=1)

saved = np.load('/tmp/mhw_interm.npz')
print("thr_sm identical:", np.array_equal(saved['thr_sm'], thr_sm2, equal_nan=True))
print("clim_sm identical:", np.array_equal(saved['clim_sm'], clim_sm2, equal_nan=True))
print("max |diff| thr:", np.nanmax(np.abs(saved['thr_sm']-thr_sm2)), " clim:", np.nanmax(np.abs(saved['clim_sm']-clim_sm2)))
np.savez_compressed('/tmp/verify_thr.npz', thr_sm2=thr_sm2, clim_sm2=clim_sm2)
print("saved verify_thr")
