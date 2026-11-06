
import os
for f in ['baseline_data.npy', 'target_data.npy', 'dates.pkl', 
          'threshold_unsmoothed.npy', 'climatology_unsmoothed.npy',
          'threshold.npy', 'climatology.npy', 'hot.npy', 'cell_mhw.npy', 'sea_mask.npy']:
    path = f'/tmp/{f}'
    print(f"{f}: {'EXISTS' if os.path.exists(path) else 'MISSING'}")
