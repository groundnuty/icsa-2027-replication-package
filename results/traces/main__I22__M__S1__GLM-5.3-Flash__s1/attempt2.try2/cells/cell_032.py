import numpy as np
W = '/work/work'
thr_raw = np.load(f'{W}/thr_raw.npy')
clim_raw = np.load(f'{W}/clim_raw.npy')
nan_t = np.isnan(thr_raw); nan_c = np.isnan(clim_raw)
print('thr NaN cells:', nan_t.sum(), '| clim NaN cells:', nan_c.sum(), '| overlap:', (nan_t & nan_c).sum())
print('NaN pattern identical:', np.array_equal(nan_t, nan_c))
# which slots / cells
idx = np.argwhere(nan_t)
print('example (slot, y, x):', idx[:5])
sl = sorted(set(idx[:, 0].tolist()))
print('slots containing NaNs:', len(sl), 'range', sl[0]+1, '->', sl[-1]+1)
# do they coincide with the 291 all-NaN land cells?
data = np.load(f'{W}/baseline_data.npy')
land = ~np.isfinite(data).any(axis=0)
print('land cells (all-NaN baseline):', land.sum())
print('NaN thr cells ⊂ land?', np.all(land[nan_t.any(axis=0)]))
print('land ⊂ NaN thr cells?', np.all(nan_t.any(axis=0)[land]))
