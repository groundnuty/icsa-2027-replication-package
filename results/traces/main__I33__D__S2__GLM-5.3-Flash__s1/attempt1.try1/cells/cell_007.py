import os
print('cwd:', os.getcwd())
try:
    import netCDF4; print('netCDF4 ok')
except Exception as e: print('netCDF4:', e)
try:
    import h5netcdf; print('h5netcdf ok')
except Exception as e: print('h5netcdf:', e)
# doy mapping check
from datetime import date, timedelta
def md_of_doy(d):
    dt = date(2000,1,1) + timedelta(days=d-1)   # 2000 is a leap year -> doy 1..366 covers all (m,d)
    return dt.month, dt.day
print('doy 1,59,60,61,153,244,366 ->', [md_of_doy(d) for d in (1,59,60,61,153,244,366)])
def doy_of(y,m,d):
    return (date(y,m,d) - date(y,1,1)).days + 1 + (1 if (m,d) >= (3,1) else 0)  # leap-anchored
# simpler: anchor to 2000
def doy_of(y,m,dd):
    return (date(2000,m,dd) - date(2000,1,1)).days + 1
print('2014-06-01 ->', doy_of(2014,6,1), ' 2014-08-31 ->', doy_of(2014,8,31))
print('1992-02-29 ->', doy_of(1992,2,29), ' 1993-03-01 ->', doy_of(1993,3,1))