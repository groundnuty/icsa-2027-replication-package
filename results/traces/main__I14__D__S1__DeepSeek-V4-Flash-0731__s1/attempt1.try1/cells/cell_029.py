
import numpy as np
import pandas as pd

target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
per_cell_mhw = np.load('/work/per_cell_mhw.npy')

# Find cells with MHW on July 8 (t=37)
t_jul8 = 37
cells_jul8 = np.where(per_cell_mhw[t_jul8])
print(f"Cells with MHW on July 8: {len(cells_jul8[0])}")
for i in range(min(len(cells_jul8[0]), 3)):
    lat_i, lon_i = cells_jul8[0][i], cells_jul8[1][i]
    print(f"  Cell ({lat_i},{lon_i})")
    # Show the MHW pattern for this cell
    mhw_seq = per_cell_mhw[:, lat_i, lon_i]
    for t in range(max(0, t_jul8-10), min(92, t_jul8+10)):
        if mhw_seq[t]:
            print(f"    {target_pd[t].date()}: MHW=True")
