
import numpy as np

hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

n_days = hot.shape[0]
n_cells = hot.shape[1]

# Count how many cells have multiple joined MHW events
multi_event_cells = []
for c in range(n_cells):
    hot_series = hot[:, c].astype(bool)
    
    # Find runs >= 5
    runs = []
    i = 0
    while i < n_days:
        if hot_series[i]:
            start = i
            while i < n_days and hot_series[i]:
                i += 1
            end = i - 1
            if end - start + 1 >= 5:
                runs.append((start, end))
        else:
            i += 1
    
    if len(runs) > 1:
        multi_event_cells.append((c, runs))

print(f'Cells with multiple runs >= 5: {len(multi_event_cells)}')
for c, runs in multi_event_cells[:10]:
    print(f'  Cell {c}: runs {runs}')
