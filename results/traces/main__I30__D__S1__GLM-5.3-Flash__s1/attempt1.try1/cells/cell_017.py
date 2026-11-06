import numpy as np, xarray as xr, datetime as dt, warnings, time, os

t0 = time.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
lat_idx = np.where((lat >= 58.69) & (lat <= 59.89))[0]
lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]

times = ds.time.values.astype('datetime64[D]')
base_lo, base_hi = np.datetime64('1991-12-27'), np.datetime64('2003-01-05')
base_sel = np.where((times >= base_lo) & (times <= base_hi))[0]
targ_sel = np.where((times >= np.datetime64('2010-06-01')) & (times <= np.datetime64('2010-08-31')))[0]

START = dt.date(1991, 12, 27)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    base_sst = ds.analysed_sst.isel(time=base_sel, latitude=lat_idx, longitude=lon_idx).load().values.astype(np.float64)
    targ_sst = ds.analysed_sst.isel(time=targ_sel, latitude=lat_idx, longitude=lon_idx).load().values.astype(np.float64)
print('loaded:', base_sst.shape, targ_sst.shape, 'in', round(time.time()-t0,1), 's')

def doy_map(d):
    y = d.timetuple().tm_yday
    if not (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) and d.month >= 3:
        return y + 1
    return y

base_dates = [START + dt.timedelta(days=int(x)) for x in (times[base_sel] - np.datetime64('1991-12-27')).astype(int)]
targ_dates = [START + dt.timedelta(days=int(x)) for x in (times[targ_sel] - np.datetime64('1991-12-27')).astype(int)]
print('base date range:', base_dates[0], base_dates[-1], 'n=', len(base_dates))
print('targ date range:', targ_dates[0], targ_dates[-1], 'n=', len(targ_dates))

# sanity on doy mapping
for d in [dt.date(1992,2,28), dt.date(1992,2,29), dt.date(1992,3,1), dt.date(1993,2,28), dt.date(1993,3,1), dt.date(1993,12,31), dt.date(1992,12,31), dt.date(2010,6,1), dt.date(2010,8,31)]:
    print(d, '->', doy_map(d))

# build pools: doy -> set of indices into base array
pool = {}
b = dt.date(1992,1,1)
while b <= dt.date(2002,12,31):
    dd = doy_map(b)
    for k in range(-5, 6):
        pool.setdefault(dd, set()).add((b + dt.timedelta(days=k) - START).days)
    b += dt.timedelta(days=1)
sizes = sorted(len(v) for v in pool.values())
print('n pool doys:', len(pool), 'pool sizes min/max:', sizes[0], sizes[-1])
print('pool size for doy1/59/61/365/366:', len(pool[1]), len(pool[59]), len(pool[61]), len(pool[365]), len(pool.get(366, [])))
print('doy 60 in pool dict:', 60 in pool)
# verify extremes
print('doy1 first/last idx dates:', START+dt.timedelta(days=min(pool[1])), START+dt.timedelta(days=max(pool[1])))
print('doy366 first/last idx dates:', START+dt.timedelta(days=min(pool[366])), START+dt.timedelta(days=max(pool[366])))
np.save('/work/base_sst.npy', base_sst); np.save('/work/targ_sst.npy', targ_sst)
