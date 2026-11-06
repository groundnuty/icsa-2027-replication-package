import numpy as np, xarray as xr, datetime as dt, time, json

ncdir = '/work/nc'
def daterange(d0, d1):
    cur = d0
    while cur <= d1:
        yield cur
        cur += dt.timedelta(days=1)

dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5))) + \
        list(daterange(dt.date(2019,6,1), dt.date(2019,8,31)))

ds0 = xr.open_dataset(f'{ncdir}/sst_{dates[0].strftime("%Y%m%d")}.nc', engine='h5netcdf')
lat32 = ds0.latitude.values; lon32 = ds0.longitude.values
lat_ref = lat32.astype(np.float64); lon_ref = lon32.astype(np.float64)
latmask = (lat_ref >= 64.51-1e-6) & (lat_ref <= 65.71+1e-6)
lonmask = (lon_ref >= 21.97-1e-6) & (lon_ref <= 23.17+1e-6)
lat_idx = np.where(latmask)[0]; lon_idx = np.where(lonmask)[0]
lat_out = lat32[lat_idx]; lon_out = lon32[lon_idx]

cube = np.full((len(dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float64)
t0=time.time(); coord_bad=0; time_bad=0
for i, d in enumerate(dates):
    fn = f"sst_{d.strftime('%Y%m%d')}.nc"
    with xr.open_dataset(f'{ncdir}/{fn}', engine='h5netcdf') as ds:
        if not (np.array_equal(ds.latitude.values, lat32) and np.array_equal(ds.longitude.values, lon32)):
            coord_bad += 1; print("COORD DIFF", fn)
        ts = str(ds.time.values[0])[:10]
        if ts != d.isoformat():
            time_bad += 1; print("TIME DIFF", fn, ts)
        cube[i] = ds.analysed_sst.values[0][np.ix_(lat_idx, lon_idx)].astype(np.float64)
print(f"verified {len(dates)} files in {time.time()-t0:.0f}s | coord_bad={coord_bad} time_bad={time_bad}")

# ---- day-of-year on 366-day calendar (month/day based, leap template) ----
def doy_md(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday
# sanity
for s in ["1992-01-01","1993-02-28","1992-02-29","1993-03-01","1999-12-31"]:
    dd = dt.date.fromisoformat(s)
    print(s, "->", doy_md(dd))
print("2019-06-01 doy:", doy_md(dt.date(2019,6,1)), "| 2019-08-31 doy:", doy_md(dt.date(2019,8,31)))

np.save('/work/cube.npy', cube)
np.save('/work/lat_out.npy', lat_out)
np.save('/work/lon_out.npy', lon_out)
with open('/work/dates.txt','w') as f:
    for d in dates: f.write(d.isoformat()+"\n")
print("cube:", cube.shape, "finite frac overall:", np.isfinite(cube).mean())
