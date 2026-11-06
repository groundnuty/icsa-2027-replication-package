import xarray as xr, numpy as np
from datetime import date
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
def gidx(dstr):
    i = int(np.searchsorted(t, np.datetime64(dstr)))
    assert t[i] == np.datetime64(dstr)
    return i
iL0 = gidx('1991-12-27'); iL1 = gidx('2020-08-31')
dates = t[iL0:iL1+1].astype('datetime64[D]')
yrs = dates.astype('datetime64[Y]').astype(int) + 1970
print('yrs sample', yrs[:5], yrs[(gidx('1992-01-01')-iL0)-2:(gidx('1992-01-01')-iL0)+3])
ys = np.array([date(int(y),1,1) for y in yrs], dtype='datetime64[D]')
doy = (dates - ys).astype('int64').astype(int) + 1
iB0, iB1 = gidx('1992-01-01'), gidx('2002-12-31')
bd = dates[iB0-iL0:iB1-iL0+1]
bdoy = doy[iB0-iL0:iB1-iL0+1]
vals, counts = np.unique(bdoy, return_counts=True)
print('doy values in baseline:', vals.min(), vals.max(), 'n distinct:', len(vals))
# which dates have doy 60?
bad = bd[bdoy==60]
print('dates with doy 60:', bad, bad.shape)
# check per year: doy of March 1 and Feb 28
for y in range(1992, 2003):
    i_m = gidx(f'{y}-03-01')-iL0
    i_f = gidx(f'{y}-02-28')-iL0
    print(y, 'feb28 doy', doy[i_f], 'mar01 doy', doy[i_m])
