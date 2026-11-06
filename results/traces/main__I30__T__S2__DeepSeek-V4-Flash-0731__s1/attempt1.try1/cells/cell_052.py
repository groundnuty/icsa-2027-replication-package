
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_time = np.load('/tmp/target_time.npy')

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
n_time, n_lat, n_lon = mhw_mask.shape

# Find a cell that's in an MHW
cells_in_mhw = np.where(mhw_mask.any(axis=0))
print("Cells with MHW:", len(cells_in_mhw[0]))

if len(cells_in_mhw[0]) > 0:
    lat_i, lon_j = cells_in_mhw[0][0], cells_in_mhw[1][0]
    print(f"Example cell: ({lat_i}, {lon_j})")
    
    # Show the hot pattern and MHW pattern for this cell
    print(f"\nHot pattern:")
    h = hot[:, lat_i, lon_j]
    m = mhw_mask[:, lat_i, lon_j]
    
    for t in range(n_time):
        if h[t] or m[t]:
            marker = ""
            if h[t]:
                marker += "H"
            if m[t]:
                marker += "M"
            print(f"  {target_dates[t].strftime('%Y-%m-%d')}: {marker}")
