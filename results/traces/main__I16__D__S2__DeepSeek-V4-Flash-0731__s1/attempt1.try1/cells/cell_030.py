
import numpy as np

# hot is (92, 60, 60) boolean
n_t = hot.shape[0]
n_lat = hot.shape[1]
n_lon = hot.shape[2]

# For each cell, find per-cell MHWs
# mhw_mask: 1 where cell is inside a per-cell MHW on that day, 0 otherwise
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

# sea_mask from previous context
# Let me reload sea_mask
import xarray as xr
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

# hot was computed in previous cell - recompute
threshold_smooth = np.load('/work/threshold_smooth.npy')
target_doys = np.array([153 + i for i in range(92)])  # June 1 = 153 to Aug 31 = 244
# Actually let me be more careful
from datetime import date
def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

target_dates = [date(2008,6,1) + timedelta(days=i) for i in range(92)]
target_doys = np.array([day_of_year(d.month, d.day) for d in target_dates])

thresh_for_target = threshold_smooth[target_doys - 1]
hot = np.zeros_like(target_data, dtype=bool)
hot[:, sea_mask] = target_data[:, sea_mask] >= thresh_for_target[:, sea_mask]

# Now find per-cell MHWs
for ilat in range(n_lat):
    for ilon in range(n_lon):
        if not sea_mask[ilat, ilon]:
            continue
        h = hot[:, ilat, ilon]  # (92,)
        
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
                if gap >= 1 and gap <= 2:
                    # Join
                    joined[-1] = (joined[-1][0], r[1])
                else:
                    joined.append(r)
            
            # Mark mask
            for start, end in joined:
                mhw_mask[start:end+1, ilat, ilon] = 1

print("Sum of mhw_mask:", np.sum(mhw_mask))
print("Cells with any MHW:", np.sum(np.any(mhw_mask, axis=0)))
