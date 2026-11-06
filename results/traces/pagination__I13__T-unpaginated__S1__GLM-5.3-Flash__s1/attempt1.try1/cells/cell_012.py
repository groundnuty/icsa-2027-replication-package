import numpy as np, pickle, warnings
warnings.filterwarnings('ignore')
cache = '/tmp/mhw_cache'
thresh_raw = np.load(f'{cache}/thresh_raw.npy')
thresh_s = np.load(f'{cache}/thresh_s.npy')
print('shapes:', thresh_raw.shape, thresh_s.shape)
d, c = 188, 971
idxs = [(d+k) % 366 or 366 for k in range(-15, 16)]
bf = thresh_raw[idxs, c].mean()
print('brute force:', bf)
print('roll-based  :', thresh_s[d, c])
print('diff:', thresh_s[d, c] - bf)
# recompute roll-based for this d manually
manual = sum(thresh_raw[(d+k) % 367, c] for k in range(-15,16)) / 31.0
print('manual (mod 367):', manual)
# check NaN rows in thresh_s
nan_rows = np.where(np.isnan(thresh_s[:, :]).all(axis=1))[0]
print('all-NaN rows in thresh_s:', nan_rows[:20])
part_nan = np.where(np.isnan(thresh_s).any(axis=1))[0]
print('rows with any NaN:', part_nan[:40], '... count:', len(part_nan))
print('thresh_s[366, :5]:', thresh_s[366, :5])
print('thresh_s[365, :5]:', thresh_s[365, :5])
print('thresh_s[1, :5]:', thresh_s[1, :5])