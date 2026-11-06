
import numpy as np

target_sst = np.load('/tmp/target_sst_f64.npy')
hot_mask_f64 = np.load('/tmp/hot_mask.npy')  # This was from the float32 version
# Let me recompute hot_mask from float64

threshold_smooth = np.load('/tmp/threshold_smooth_f64.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_times = np.load('/tmp/target_times.npy')
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])
n_time, n_lat, n_lon = target_sst.shape

hot_mask = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    thresh = threshold_smooth[doy-1, :, :]
    sst = target_sst[t, :, :]
    hot_mask[t] = (sst >= thresh) & np.isfinite(sst) & np.isfinite(thresh)

# Check for cells where joining might be ambiguous
# Look for cells with hot runs < 5 days between MHWs
mhw_mask = np.load('/tmp/mhw_mask_f64.npy')

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i,j]:
            continue
        hot = hot_mask[:, i, j]
        mhw = mhw_mask[:, i, j]
        
        # Find MHW runs
        mhw_runs = []
        start = None
        for t in range(n_time):
            if mhw[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    mhw_runs.append((start, t-1))
                    start = None
        if start is not None:
            mhw_runs.append((start, n_time-1))
        
        # Check if there are hot days between MHW runs
        if len(mhw_runs) >= 2:
            for k in range(len(mhw_runs) - 1):
                end_first = mhw_runs[k][1]
                start_second = mhw_runs[k+1][0]
                gap = start_second - end_first - 1
                if gap > 0:
                    # Check if any days in the gap are hot
                    gap_hot = hot[end_first+1:start_second]
                    if np.any(gap_hot):
                        print(f"Cell ({i},{j}): MHW runs {mhw_runs[k]} and {mhw_runs[k+1]}, gap={gap} days, {gap_hot.sum()} hot in gap")

print("Done checking")
