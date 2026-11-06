import numpy as np
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy'); sea = np.load('/work/sea.npy')
print('nan cells in thr_s (any day):', np.isnan(thr_s).any(axis=0).sum())
print('nan cells in clim_s (any day):', np.isnan(clim_s).any(axis=0).sum())
# are NaN cells exactly complement of sea?
nan_cells = np.isnan(thr_s).any(axis=0)
print('nan cells subset of non-sea:', (nan_cells & sea).sum() == 0)
print('non-sea count:', (~sea).sum(), 'nan thr cells:', nan_cells.sum())
# any non-sea cell that is NOT nan-thr? (i.e., had baseline data but not target data)
print('non-sea cells with finite thr:', ((~sea) & ~nan_cells).sum())
