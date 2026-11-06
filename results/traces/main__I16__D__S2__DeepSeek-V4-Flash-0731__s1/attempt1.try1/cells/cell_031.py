
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

target_times = target_region.time.values
target_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
                for t in target_times]
target_doys = np.array([day_of_year(d.month, d.day) for d in target_dates])
print("Target doys:", target_doys[0], "to", target_doys[-1])

thresh_for_target = threshold_smooth[target_doys - 1]  # (92, 60, 60)
hot = np.zeros_like(target_data, dtype=bool)
hot[:, sea_mask] = target_data[:, sea_mask] >= thresh_for_target[:, sea_mask]

n_t, n_lat, n_lon = hot.shape

# Find per-cell MHWs
mhw_mask = np.zeros((n_t, n_lat, n_lon), dtype=np.uint8)

for ilat in range(n_lat):
    for ilon in range(n_lon):
        if not sea_mask[ilat, ilon]:
            continue
        h = hot[:, ilat, ilon]
        
        # Find runs of consecutive hot days
        runs = []
        i = 0
        while i < n_t:
            if h[i]:
                start = i
                while i < n_t and h[i]:
                    i += 1
                runs.append((start, i-1))
            else:
                i += 1
        
        # Keep runs of length >= 5
        mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join MHWs separated by 1 or 2 non-hot days
        if mhw_runs:
            joined = [mhw_runs[0]]
            for r in mhw_runs[1:]:
                prev_end = joined[-1][1]
                gap = r[0] - prev_end - 1
                if 1 <= gap <= 2:
                    joined[-1] = (joined[-1][0], r[1])
                else:
                    joined.append(r)
            
            for start, end in joined:
                mhw_mask[start:end+1, ilat, ilon] = 1

print("Sum of mhw_mask:", np.sum(mhw_mask))
print("Cells with any MHW:", np.sum(np.any(mhw_mask, axis=0)))
print("mhw_mask dtype:", mhw_mask.dtype)
np.save('/work/mhw_mask.npy', mhw_mask)
