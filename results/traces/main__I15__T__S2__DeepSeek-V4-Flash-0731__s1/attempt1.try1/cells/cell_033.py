
import numpy as np
import pandas as pd

per_cell_mhw = np.load('per_cell_mhw.npy')
sea_cells = np.load('sea_cells.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')

# Find cells with MHWs
cells_with_mhw = np.any(per_cell_mhw, axis=0)
print('Cells with per-cell MHWs:', cells_with_mhw.sum())

# Find the first few such cells and show their MHW patterns
count = 0
for i in range(per_cell_mhw.shape[1]):
    for j in range(per_cell_mhw.shape[2]):
        if cells_with_mhw[i, j]:
            mhw_days = per_cell_mhw[:, i, j]
            # Find runs
            runs = []
            in_run = False
            for t in range(len(mhw_days)):
                if mhw_days[t]:
                    if not in_run:
                        start = t
                        in_run = True
                else:
                    if in_run:
                        runs.append((start, t-1))
                        in_run = False
            if in_run:
                runs.append((start, len(mhw_days)-1))
            
            print(f'Cell ({i},{j}): MHW runs: ', end='')
            for s, e in runs:
                print(f'[{pd.Timestamp(target_time[s]).strftime("%m-%d")} to {pd.Timestamp(target_time[e]).strftime("%m-%d")}]', end=' ')
            print()
            count += 1
            if count >= 10:
                break
    if count >= 10:
        break
