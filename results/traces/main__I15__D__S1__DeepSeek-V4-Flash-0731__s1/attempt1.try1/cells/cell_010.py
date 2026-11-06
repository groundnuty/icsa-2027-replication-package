
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values

# Region: lat 56.13 to 57.33, lon 17.71 to 18.91
lat_mask = (lat >= 56.13) & (lat <= 57.33)
lon_mask = (lon >= 17.71) & (lon <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("Lat values:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("Lon values:", lon[lon_idx[0]], lon[lon_idx[-1]])

# Define the day-of-year mapping
def date_to_doy(dt):
    """Map date to day of year from 1 to 366: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366"""
    year = dt.year
    month = dt.month
    day = dt.day
    # Days before this month
    month_start_doy = {1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153, 7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336}
    # Check leap year
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    # Adjust: if leap year and month >= 3, add 1
    doy = month_start_doy[month] + day - 1
    if is_leap and month >= 3:
        doy += 1
    # But this mapping means: non-leap: Jan1=1, Feb28=59, Mar1=60...
    # The task says: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366
    # So day 60 only exists in leap years (Feb 29). Non-leap years have no day 60.
    # Actually, let me re-read: "Map every date to a day of year from 1 to 366 by month and day: 
    # 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, …, 31 December = 366"
    # So this is a fixed mapping independent of the year. Day 60 = Feb 29 (leap only).
    # This means: Jan 1 = 1, Jan 31 = 31, Feb 1 = 32, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61...
    # This is just: for non-leap years, the doy matches standard; for leap years, it also matches standard 
    # except the standard leap-year doy has Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, etc.
    # So actually this IS the standard day-of-year where leap year has 366 days.
    # The key point: day 60 only exists in leap years (Feb 29).
    return doy

# Test
import datetime
for d in [datetime.date(1992,1,1), datetime.date(1992,2,28), datetime.date(1992,2,29), datetime.date(1992,3,1), datetime.date(1993,1,1), datetime.date(1993,2,28), datetime.date(1993,3,1), datetime.date(2019,12,31)]:
    print(d, "->", date_to_doy(d))
