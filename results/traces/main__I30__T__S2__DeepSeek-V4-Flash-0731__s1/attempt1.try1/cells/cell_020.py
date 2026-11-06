
import numpy as np

hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

n_time, n_lat, n_lon = hot.shape

# For each sea cell, find per-cell MHWs
# Result: mhw_mask[time, lat, lon] = True if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros_like(hot)

for lat_i in range(n_lat):
    for lon_j in range(n_lon):
        if not sea_mask[lat_i, lon_j]:
            continue
        
        h = hot[:, lat_i, lon_j]
        
        # Find runs of consecutive hot days
        # Find transitions
        runs = []  # list of (start, end) inclusive indices
        i = 0
        while i < n_time:
            if h[i]:
                start = i
                while i < n_time and h[i]:
                    i += 1
                end = i - 1
                runs.append((start, end))
            else:
                i += 1
        
        # MHWs: runs with length >= 5
        mhws = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not mhws:
            continue
        
        # Join MHWs separated by 1 or 2 non-hot days
        joined = []
        current = list(mhws[0])
        for next_mhw in mhws[1:]:
            gap = next_mhw[0] - current[1] - 1
            if 1 <= gap <= 2:
                # Join
                current[1] = next_mhw[1]
            else:
                joined.append(tuple(current))
                current = list(next_mhw)
        joined.append(tuple(current))
        
        # Mark all days in joined MHWs
        for s, e in joined:
            mhw_mask[s:e+1, lat_i, lon_j] = True

print("mhw_mask shape:", mhw_mask.shape)
print("Total MHW days:", mhw_mask.sum())
print("MHW cells per day:", mhw_mask.sum(axis=(1,2)))
