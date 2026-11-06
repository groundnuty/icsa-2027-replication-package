
import numpy as np
import pandas as pd

mhw_mask = np.load('mhw_mask.npy')
target_data = xr.open_dataset('target_data.nc')
target_time = target_data.time.values
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Cell (11,37)
la, lo = 11, 37
cell_mhw = mhw_mask[:, la, lo]

print("MHW status for cell (11,37):")
for t in range(len(target_time)):
    if cell_mhw[t]:
        print(f"  {target_dates[t].strftime('%Y-%m-%d')}: mhw=1")
