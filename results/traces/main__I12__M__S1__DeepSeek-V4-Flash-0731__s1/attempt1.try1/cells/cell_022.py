
import numpy as np

per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')

# Check cells in MHW on days 36-40
for t in range(36, 41):
    cells = np.argwhere(per_cell_mhw[t])
    print(f"Day {t}: {len(cells)} cells in MHW")
    if len(cells) > 0:
        print(f"  First few: {cells[:5]}")
