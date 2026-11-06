import numpy as np, datetime as dt, os
S = np.load('/tmp/mhw/S32.npy')
dates = np.load('/tmp/mhw/dates.npy')
n_base_ext, n_tgt = 4028, 92
print(S.shape, len(dates))

S64 = S.astype(np.float64)
tgt = S64[n_base_ext:]  # (92,60,60)
finite_all = np.isfinite(tgt).all(axis=0)
print('sea cells (finite every target day):', int(finite_all.sum()))
np.save('/tmp/mhw/sea.npy', finite_all)

# per-cell count of non-finite target days among cells not 'sea'
bad = (~np.isfinite(tgt)).sum(axis=0)
print('cells with >=1 non-finite target day:', int((bad>0).sum()), 'max nonfinite days in such cells:', int(bad[~finite_all].max()) if (~finite_all).any() else 0)

# check baseline coverage per cell: all sea cells should have data on all 4028 baseline days
base = S64[:n_base_ext]
fin_base = np.isfinite(base).sum(axis=0)
print('nonfinite baseline days per sea cell: min/max', int(fin_base[finite_all].min()), int(fin_base[finite_all].max()))
print('mean SST by year (sea cells):')
years = [d[:4] for d in dates]
import collections
for y in sorted(set(years)):
    idx = [k for k,dd in enumerate(dates) if dd[:4]==y]
    m = np.nanmean(S64[idx][:, finite_all])
    print(' ', y, round(float(m),2))
