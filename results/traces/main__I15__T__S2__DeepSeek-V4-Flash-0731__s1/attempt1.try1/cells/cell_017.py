
import numpy as np
import pickle

# Recompute or load... let me redo it more efficiently by saving the arrays
sst_base = np.load('sst_base.npy')
with open('pools.pkl', 'rb') as f:
    pools = pickle.load(f)

n_lat, n_lon = sst_base.shape[1], sst_base.shape[2]

threshold = np.full((367, n_lat, n_lon), np.nan)
climatology = np.full((367, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pools[doy]
    if not idx:
        continue
    data = sst_base[idx, :, :].astype(np.float64)
    for i in range(n_lat):
        for j in range(n_lon):
            vals = data[:, i, j]
            valid = ~np.isnan(vals)
            if valid.sum() > 0:
                threshold[doy, i, j] = np.percentile(vals[valid], 90, method='hazen')
                climatology[doy, i, j] = np.mean(vals[valid])

# Set day 60 to mean of days 59 and 61
for i in range(n_lat):
    for j in range(n_lon):
        t59, t61 = threshold[59, i, j], threshold[61, i, j]
        c59, c61 = climatology[59, i, j], climatology[61, i, j]
        if not np.isnan(t59) and not np.isnan(t61):
            threshold[60, i, j] = (t59 + t61) / 2
        elif not np.isnan(t59):
            threshold[60, i, j] = t59
        elif not np.isnan(t61):
            threshold[60, i, j] = t61
        # Same for climatology
        if not np.isnan(c59) and not np.isnan(c61):
            climatology[60, i, j] = (c59 + c61) / 2
        elif not np.isnan(c59):
            climatology[60, i, j] = c59
        elif not np.isnan(c61):
            climatology[60, i, j] = c61

# Save
np.save('threshold_raw.npy', threshold)
np.save('climatology_raw.npy', climatology)

print('Day 60 set. Checking sample cell:')
print('  Threshold[59,30,30]:', threshold[59, 30, 30])
print('  Threshold[60,30,30]:', threshold[60, 30, 30])
print('  Threshold[61,30,30]:', threshold[61, 30, 30])
print('  Clim[59,30,30]:', climatology[59, 30, 30])
print('  Clim[60,30,30]:', climatology[60, 30, 30])
print('  Clim[61,30,30]:', climatology[61, 30, 30])
