import numpy as np, datetime as dtm, time

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # cumulative month starts, leap-style
def doy_of(dates):  # dates: datetime64[D] array
    months = dates.astype('datetime64[M]')
    m = (months - months.astype('datetime64[Y]')).astype(int)      # 0..11
    day = (dates - months).astype(int) + 1
    return cum[m] + day

tests = [('2009-06-01',153),('2009-08-31',244),('1992-02-29',60),('1993-02-28',59),
         ('1993-03-01',61),('2000-12-31',366),('1993-12-31',366),('2009-01-01',1),
         ('1992-03-01',61),('1996-02-28',59),('1900-03-01',61)]
ok = True
for s, exp in tests:
    got = int(doy_of(np.array(np.datetime64(s), dtype='datetime64[D]')))
    if got != exp: ok = False; print('MISMATCH', s, got, exp)
print('doy mapping all OK:', ok)

def date_of_doy(d, y):
    d = int(d)
    if d <= 59:
        return np.datetime64(f'{y:04d}-01-01') + np.timedelta64(d-1, 'D')
    m = np.searchsorted(cum, d, side='right') - 1   # last month with cum[m] < d
    return np.datetime64(f'{y:04d}-{m+1:02d}-{d-cum[m]:02d}')
for d, y, exp in [(1,1992,'1992-01-01'),(59,1993,'1993-02-28'),(61,1993,'1993-03-01'),
                  (61,1992,'1992-03-01'),(244,2009,'2009-09-01') if False else (244,2009,'2009-09-01'),
                  (366,2002,'2002-12-31'),(153,2009,'2009-06-01'),(244,2009,'2009-08-31')]:
    if d in (244,):
        exp = '2009-08-31' if d==244 else exp
    got = str(date_of_doy(d,y))
    if got != exp: print('MISMATCH', d, y, got, exp)
print('date_of_doy spot checks done')

# load timing test: 400 consecutive days of the region
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
i0 = np.searchsorted(t, np.datetime64('1991-12-27'))
t0 = time.time()
blk = ds.analysed_sst.isel(time=slice(i0, i0+400), latitude=slice(130,190), longitude=slice(78,138)).values
t1 = time.time()
print('loaded', blk.shape, blk.dtype, 'in', round(t1-t0,1), 's -> full 4033+92 approx', round((t1-t0)*4125/400,1), 's')
print('NaN frac in this block:', np.mean(~np.isfinite(blk)))