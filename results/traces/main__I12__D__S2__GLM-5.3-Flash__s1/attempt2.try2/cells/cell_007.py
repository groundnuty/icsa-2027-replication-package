import numpy as np, time
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def date_of_doy(d, y):
    m = np.searchsorted(cum, d, side='left') - 1   # largest m with cum[m] < d
    return np.datetime64(f'{y:04d}-{m+1:02d}-{d-cum[m]:02d}')
def doy_of(dates):
    months = dates.astype('datetime64[M]')
    m = (months - months.astype('datetime64[Y]')).astype(int)
    return cum[m] + ((dates - months).astype(int) + 1)

ok = True
for d, y, exp in [(1,1992,'1992-01-01'),(59,1993,'1993-02-28'),(60,1992,'1992-02-29'),
                  (61,1993,'1993-03-01'),(61,1992,'1992-03-01'),(213,1992,'1992-07-31'),
                  (214,1992,'1992-08-01'),(244,2009,'2009-08-31'),(366,2002,'2002-12-31'),
                  (153,2009,'2009-06-01'),(335,1993,'1993-12-01'),(336,1992,'1992-12-01')]:
    got = str(date_of_doy(d,y))
    if got != exp: ok=False; print('MISMATCH', d, y, got, exp)
# roundtrip: all days of a leap and non-leap year
for y in (1992, 1993, 2000, 2001):
    nd = 366 if (y%4==0 and (y%100!=0 or y%400==0)) else 365
    ds_ = np.datetime64(f'{y}-01-01') + np.arange(nd).astype('timedelta64[D]')
    r = np.array([doy_of(np.array(d, dtype='datetime64[D]')[np.newaxis])[0] for d in ds_])
    if not np.array_equal(r, np.arange(1, nd+1)): ok=False; print('roundtrip fail', y)
    back = [date_of_doy(int(dd), y) for dd in np.unique(r)]
    if not all(str(a)==str(b) for a,b in zip(back, ds_[np.unique(r, return_index=True)[1]])): ok=False; print('back fail', y)
print('date_of_doy + roundtrip all OK:', ok)

import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
i0 = np.searchsorted(t, np.datetime64('1991-12-27'))
t0 = time.time()
blk = ds.analysed_sst.isel(time=slice(i0, i0+400), latitude=slice(130,190), longitude=slice(78,138)).values
t1 = time.time()
print('loaded', blk.shape, blk.dtype, 'in', round(t1-t0,1), 's -> est full', round((t1-t0)*4125/400,1), 's')
print('NaN frac:', np.mean(~np.isfinite(blk)), 'min/max:', np.nanmin(blk), np.nanmax(blk))