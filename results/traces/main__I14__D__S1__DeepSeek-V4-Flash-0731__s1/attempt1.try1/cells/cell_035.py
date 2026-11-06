
import numpy as np
import pandas as pd

target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
per_cell_mhw = np.load('/work/per_cell_mhw.npy')

# Check if any cell has MHW with gaps (non-hot days inside the MHW)
# These would be from joined MHWs
n_time, n_lat, n_lon = per_cell_mhw.shape

joined_cells = []
for lat_i in range(n_lat):
    for lon_i in range(n_lon):
        mhw_seq = per_cell_mhw[:, lat_i, lon_i]
        # Find MHW segments and check for internal gaps
        if np.any(mhw_seq):
            # Check if there are any 0s between 1s (internal gaps in the MHW)
            ones = np.where(mhw_seq)[0]
            if len(ones) > 0:
                for k in range(len(ones)-1):
                    if ones[k+1] - ones[k] > 1:
                        joined_cells.append((lat_i, lon_i, ones[k], ones[k+1]))
                        break

print(f"Cells with joined MHWs (internal gaps): {len(joined_cells)}")
for cell in joined_cells[:5]:
    lat_i, lon_i, s, e = cell
    print(f"  Cell ({lat_i},{lon_i}): gap between day {s} ({target_pd[s].date()}) and day {e} ({target_pd[e].date()})")
    # Show the hot and MHW patterns
    print("  Day       Hot   MHW")
    for t in range(max(0, s-2), min(n_time, e+3)):
        print(f"  {target_pd[t].date()}  {hot[t, lat_i, lon_i]}  {mhw_seq[t]}")
