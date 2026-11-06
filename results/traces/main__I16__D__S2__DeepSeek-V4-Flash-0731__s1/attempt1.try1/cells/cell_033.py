
import numpy as np
import xarray as xr
from datetime import date, timedelta

def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]
time = ds.time.values
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]
target_region = ds['analysed_sst'].isel(time=slice(t_start, t_end+1),
                                        latitude=lat_idx, longitude=lon_idx).load()
target_data = target_region.values.astype(np.float64)
sea_mask = np.all(np.isfinite(target_data), axis=0)

threshold_smooth = np.load('/work/threshold_smooth.npy')
mhw_mask = np.load('/work/mhw_mask.npy')

# Find a sea cell with MHW
ilat_has_mhw, ilon_has_mhw = np.where(np.any(mhw_mask, axis=0))
print("Number of cells with MHW:", len(ilat_has_mhw))

# Examine the first one
ilat, ilon = ilat_has_mhw[0], ilon_has_mhw[0]
print(f"\nCell ({ilat}, {ilon}), lat={lat[lat_idx[ilat]]}, lon={lon[lon_idx[ilon]]}")

# Target dates
target_times = target_region.time.values
target_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
                for t in target_times]
target_doys = np.array([day_of_year(d.month, d.day) for d in target_dates])

# Show SST, threshold, hot, mhw for this cell
print("Date | doy | SST | threshold | hot | mhw")
for i in range(92):
    sst = target_data[i, ilat, ilon]
    thr = threshold_smooth[target_doys[i]-1, ilat, ilon]
    h = sst >= thr
    m = mhw_mask[i, ilat, ilon]
    if m or h:
        print(f"{target_dates[i]} | {target_doys[i]:3d} | {sst:.2f} | {thr:.2f} | {h} | {m}")
