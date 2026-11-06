import fsspec, xarray as xr, numpy as np, datetime as dt, os, json, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
I0,I1,J0,J1 = 130,190,78,138

d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
t0d = dt.date(2021,6,1); t1d = dt.date(2021,8,31)
dates = []
d = d0
while d <= d1:
    dates.append(d); d += dt.timedelta(days=1)
d = t0d
while d <= t1d:
    dates.append(d); d += dt.timedelta(days=1)
nd = len(dates)
print('days to read:', nd)

cache = '/tmp/mhw_cache'; os.makedirs(cache, exist_ok=True)
CH = 400
nch = (nd + CH - 1)//CH
ref_lat = ref_lon = None
t_start = time.time()
for ci in range(nch):
    fp = f'{cache}/chunk_{ci:03d}.npy'
    if os.path.exists(fp):
        continue
    m = min(CH, nd - ci*CH)
    arr = np.full((m, 60, 60), np.nan, dtype='float32')
    for k, dd in enumerate(dates[ci*CH:ci*CH+m]):
        s = dd.strftime('%Y%m%d')
        with fs.open(f'{base}/sst_{s}.nc','rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            tv = ds['time'].values[0]
            assert np.datetime64(dd) == tv.astype('datetime64[D]'), (s, tv)
            la = ds['latitude'].values; lo = ds['longitude'].values
            if ref_lat is None:
                ref_lat, ref_lon = la, lo
            else:
                assert np.array_equal(la, ref_lat) and np.array_equal(lo, ref_lon), s
            arr[k] = ds['analysed_sst'][0, I0:I1, J0:J1].values
            ds.close()
    np.save(fp, arr)
    np.save(f'{cache}/ref_lat.npy', ref_lat)
    np.save(f'{cache}/ref_lon.npy', ref_lon)
    print('chunk', ci, 'done', round(time.time()-t_start,1), 's', flush=True)
print('total read time', round(time.time()-t_start,1), 's')

cube = np.full((nd,60,60), np.nan, dtype='float32')
for ci in range(nch):
    a = np.load(f'{cache}/chunk_{ci:03d}.npy')
    cube[ci*CH:ci*CH+len(a)] = a
np.save(f'{cache}/cube.npy', cube)
with open(f'{cache}/dates.json','w') as f:
    json.dump([dd.isoformat() for dd in dates], f)
print('cube', cube.shape, 'finite frac', round(float(np.isfinite(cube).mean()),4))
# split: baseline part (1991-12-27..2003-01-05) then target
nb = (d1 - d0).days + 1
print('baseline days:', nb, 'target days:', nd-nb)
print('target start/end:', dates[nb], dates[-1])