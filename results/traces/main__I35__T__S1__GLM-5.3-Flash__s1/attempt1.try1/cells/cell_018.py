import numpy as np, datetime as dt
print('numpy', np.__version__)
import xarray, h5py
print('xarray', xarray.__version__, 'h5py', h5py.__version__)
try:
    import scipy; print('scipy', scipy.__version__)
except Exception as e: print('no scipy')

def doy_of(d):
    y = d.timetuple().tm_yday
    import calendar
    if calendar.isleap(d.year):
        return y
    return y+1 if y>=60 else y
# checks
tests = {(dt.date(2009,1,1)):1, (dt.date(2009,2,28)):59, (dt.date(2012,2,28)):59, (dt.date(2012,2,29)):60,
         (dt.date(2009,3,1)):61, (dt.date(2012,3,1)):61, (dt.date(2009,12,31)):366, (dt.date(2012,12,31)):366,
         (dt.date(1992,2,29)):60, (dt.date(1993,3,1)):61, (dt.date(1993,12,31)):366, (dt.date(2009,6,1)):152, (dt.date(2009,8,31)):243}
for d,v in tests.items():
    got=doy_of(d)
    print(d, got, 'OK' if got==v else f'MISMATCH expected {v}')
