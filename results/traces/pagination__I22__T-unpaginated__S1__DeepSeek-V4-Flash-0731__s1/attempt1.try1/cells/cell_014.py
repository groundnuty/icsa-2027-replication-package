
import numpy as np

# Load raw threshold and climatology
threshold = np.load('cache/threshold_raw.npy')
clim = np.load('cache/clim_raw.npy')

def smooth_366(arr):
    """Apply unweighted centred 31-day moving mean that wraps around (mod 366)."""
    # arr: (366, ...) array
    # For day d, average days d-15 ... d+15, counted modulo 366
    n = 366
    window = 31
    half = 15
    
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d - half + k) % n for k in range(window)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

print('Smoothing threshold...')
threshold_sm = smooth_366(threshold)
print('Smoothing climatology...')
clim_sm = smooth_366(clim)

print(f'NaN in smoothed threshold: {np.isnan(threshold_sm).sum()}')
print(f'NaN in smoothed clim: {np.isnan(clim_sm).sum()}')

# Check a sample
print('\nSmoothed values for cell (30,30):')
for doy in [1, 59, 60, 61, 100, 152, 153, 154, 200, 300, 366]:
    print(f'  doy {doy}: thresh={threshold_sm[doy-1, 30, 30]:.4f}, clim={clim_sm[doy-1, 30, 30]:.4f}')

# Save smoothed results
np.save('cache/threshold_smoothed.npy', threshold_sm)
np.save('cache/clim_smoothed.npy', clim_sm)
print('Saved smoothed results')
