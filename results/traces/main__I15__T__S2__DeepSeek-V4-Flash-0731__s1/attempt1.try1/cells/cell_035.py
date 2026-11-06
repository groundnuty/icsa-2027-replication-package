
import numpy as np
import pandas as pd

per_cell_mhw = np.load('per_cell_mhw.npy')
sea_cells = np.load('sea_cells.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')

# Active days
active = np.zeros(len(target_time), dtype=bool)
for t in range(len(target_time)):
    active[t] = np.any(per_cell_mhw[t] & sea_cells)

print('Active days:')
for t in range(len(target_time)):
    if active[t]:
        print(f'  {pd.Timestamp(target_time[t]).strftime("%Y-%m-%d")}')

print(f'\nTotal active days: {active.sum()}')
