import numpy as np, os, json, time
base = "/data/icsa2027_data_20261101T090944Z/s1z"
import h5py
p = f"{base}/sst_19920601.nc"
with h5py.File(p, "r") as fh:
    lat = fh["latitude"][:]
    lon = fh["longitude"][:]

lat_idx = np.where((lat >= 62.25 - 1e-6) & (lat <= 63.45 + 1e-6))[0]
lon_idx = np.where((lon >= 18.73 - 1e-6) & (lon <= 19.93 + 1e-6))[0]
print("nlat", len(lat_idx), "nlon", len(lon_idx))
print("lat range:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon range:", lon[lon_idx[0]], lon[lon_idx[-1]])

# Precompute the sorted list of baseline-window dates per day-of-year (1..366)
from datetime import date, timedelta
baseline_start = date(1992,1,1); baseline_end = date(2002,12,31)
doy = lambda dt: (dt.month, dt.day)  # placeholder
def day_of_year(dt):
    # month/day mapping: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61 ... 31 Dec=366
    m, dd = dt.month, dt.day
    if m == 1: return dd
    if m == 2: return 31 + dd
    # for Mar..Dec, doy = 60 + daynumber within Mar-Dec where Mar 1 = 61
    # cumulative days before month m in a leap year: 
    cum = [0,31,60,91,121,152,122, # dummy
    return None
