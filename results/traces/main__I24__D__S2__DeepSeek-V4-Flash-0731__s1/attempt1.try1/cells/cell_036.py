
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60) uint8
target_time = np.load('/work/target_time.npy', allow_pickle=True)
tt = pd.to_datetime(target_time)
target_sst = np.load('/work/target_sst.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')

# Find cells where MHW days are not all consecutive (indicating gap joining)
for lat_i in range(60):
    for lon_i in range(60):
        mhw_days = np.where(mhw_mask[:, lat_i, lon_i] > 0)[0]
        if len(mhw_days) > 0:
            # Check if there are gaps
            diffs = np.diff(mhw_days)
            if np.any(diffs > 1):
                print(f"Cell ({lat_i}, {lon_i}): MHW days = {mhw_days}, diffs = {diffs}")
                # Check if this involves gap joining
                # Check hot days
                cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
                def doy_from_md(m, d):
                    return cum[m-1] + d
                target_doy = np.array([doy_from_md(t.month, t.day) for t in tt])
                hot = np.zeros(92, dtype=bool)
                for i in range(92):
                    d_idx = target_doy[i] - 1
                    hot[i] = target_sst[i, lat_i, lon_i] >= threshold_smooth[d_idx, lat_i, lon_i]
                hot_days = np.where(hot)[0]
                print(f"  Hot days: {hot_days}")
                # Find runs
                runs = []
                i = 0
                n = len(hot)
                while i < n:
                    if hot[i]:
                        start = i
                        while i < n and hot[i]:
                            i += 1
                        end = i - 1
                        runs.append((start, end))
                    else:
                        i += 1
                mhw_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
                print(f"  MHW runs (>=5): {mhw_runs}")
                # Check if joined
                if len(mhw_runs) > 1:
                    print(f"  ** Multiple MHW runs - checking if joined **")
                    print(f"  MHW mask days: {mhw_days}")
                break
    else:
        continue
    break
