import numpy as np, xarray as xr, os, datetime as dt, time

ncdir = '/work/nc'
def daterange(d0, d1):
    cur = d0
    while cur <= d1:
        yield cur
        cur += dt.timedelta(days=1)

dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5))) + \
        list(daterange(dt.date(2019,6,1), dt.date(2019,8,31)))

# reference coords from first file
ds0 = xr.open_dataset(f'{ncdir}/sst_{dates[0].strftime("%Y%m%d")}.nc', engine='h5netcdf')
lat_ref = ds0.latitude.values.astype(np.float64)
lon_ref = ds0.longitude.values.astype(np.float64)
latmask = (lat_ref >= 64.51-1e-6) & (lat_ref <= 65.71+1e-6)
lonmask = (lon_ref >= 21.97-1e-6) & (lon_ref <= 23.17+1e-6)
lat_idx = np.where(latmask)[0]; lon_idx = np.where(lonmask)[0]
nlat, nlon = len(lat_idx), len(lon_idx)
print("region:", nlat, "x", nlon, "| lat", lat_ref[lat_idx][0], lat_ref[lat_idx][-1], "| lon", lon_ref[lon_idx][0], lon_ref[lon_idx][-1])
lat_out = lat_ref[lat_idx]; lon_out = lon_ref[lon_idx]

cube = np.full((len(dates), nlat, nlon), np.nan, dtype=np.float64)
t0 = time.time()
bad = []
for i, d in enumerate(dates):
    fn = f"sst_{d.strftime('%Y%m%d')}.nc"
    with xr.open_dataset(f'{ncdir}/{fn}', engine='h5netcdf') as ds:
        lat = ds.latitude.values; lon = ds.longitude.values
        if not (np.array_equal(lat, ds0.latitude.values) and np.array_equal(lon, ds0.longitude.values)):
            bad.append((d.isoformat(), 'coords differ'))
            continue
        tv = ds.time.values[0]
        td = dt.datetime.utcfromtimestamp(tv.astype('datetime64[s]').astype('O').timestamp()).date()
        if td != d:
            bad.append((d.isoformat(), f'time={td}'))
        arr = ds.analysed_sst.values[0][np.ix_(lat_idx, lon_idx)].astype(np.float64)
    cube[i] = arr
    if i % 1000 == 0:
        print(i, d, f"{time.time()-t0:.0f}s", flush=True)
print("cube shape:", cube.shape, "built in", f"{time.time()-t0:.0f}s")
print("coord/time anomalies:", bad)
print("overall finite frac:", np.isfinite(cube).mean())
np.save('/work/cube.npy', cube)
np.save('/work/lat_out.npy', lat_out)
np.save('/work/lon_out.npy', lon_out)
with open('/work/dates.txt','w') as f:
    for d in dates: f.write(d.isoformat()+"\n")
# memory check
import resource
print("max rss GB:", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6)
