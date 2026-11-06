
import numpy as np
import pandas as pd

per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Active day: at least one sea cell in an MHW
# per_cell_mhw already only marks sea cells in MHWs (land cells are all False)
active = per_cell_mhw.any(axis=(1, 2))
print(f"Active days: {active.sum()}")

# Show active days
tgt_start = pd.Timestamp('2007-06-01')
for t in range(92):
    if active[t]:
        d = tgt_start + pd.Timedelta(days=t)
        print(f"  Day {t}: {d.date()} active, {per_cell_mhw[t].sum()} cells in MHW")
