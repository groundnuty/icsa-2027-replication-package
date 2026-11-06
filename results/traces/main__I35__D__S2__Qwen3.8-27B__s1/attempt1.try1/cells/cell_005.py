import xarray as xr
import numpy as np
import numpy.__init__ as npi
print('numpy', np.__version__)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds['time'].values
print('time dtype:', t.dtype, 'first:', t[0], 'last:', t[-1], 'n:', len(t))
# continuity check
diffs = np.diff(t.astype('int64')) // 86400000000000
print('time diffs all 1?', np.all(diffs == 1))
# indices for needed dates
import datetime as dt
def idx(d):
    ts = np.datetime64(d)
    i = np.searchsorted(t, ts)
    assert t[i] == ts, (d, t[i])
    return i
i_ext0 = idx('1991-12-27'); i_ext1 = idx('2003-01-05')
i_t0 = idx('2009-06-01'); i_t1 = idx('2009-08-31')
i_b0 = idx('1992-01-01'); i_b1 = idx('2002-12-31')
print('ext range:', i_ext0, i_ext1, '->', (i_ext1-i_ext0+1), 'days')
print('target:', i_t0, i_t1, '->', (i_t1-i_t0+1), 'days')
print('baseline:', i_b0, i_b1, '->', (i_b1-i_b0+1), 'days')
# verify day-of-year mapping idea (leap-year ordinal)
doy_leap = (t.astype('datetime64[D]') - np.datetime64('2000-01-01')).astype('int64') + 1
def doy_leap_of(m, d):
    y = dt.date(2000, m, d)
    return (y - dt.date(2000,1,1)).days + 1
print('check: 1993-03-01 doy =', doy_leap[idx('1993-03-01')], '(expect 61)')
print('check: 2000-02-29 doy =', doy_leap[idx('2000-02-29')], '(expect 60)')
print('check: 2009-06-01 doy =', doy_leap[idx('2009-06-01')], '(expect 153)')
print('check: 2009-08-31 doy =', doy_leap[idx('2009-08-31')], '(expect 243)')
print('check: 2009-02-28 doy =', doy_leap[idx('2009-02-28')], '(expect 59)')
