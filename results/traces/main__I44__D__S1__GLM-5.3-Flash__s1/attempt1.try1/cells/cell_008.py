import numpy as np, datetime as dt, pickle
data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: all_dates=pickle.load(fh)
d0=all_dates[0]; D = np.array([(d-d0).days for d in all_dates])

t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
print('target slice', ti0, ti1, 'days', ti1-ti0+1)
target=data[ti0:ti1+1]
finite_all = np.isfinite(target).all(axis=0)
print('sea cells (finite all 92 target days):', finite_all.sum(), 'of 3600')
print('target-day NaN cells per day min/max:', np.isfinite(target).sum(axis=(1,2)).min(), np.isfinite(target).sum(axis=(1,2)).max())
print('target-day NaN count for first day:', (~np.isfinite(target[0])).sum())
print('days with all-NaN in target:', [str(all_dates[ti0+k]) for k in range(target.shape[0]) if (~np.isfinite(target[k])).all()])

base = data[(D>=(dt.date(1992,1,1)-d0).days)&(D<=(dt.date(2002,12,31)-d0).days)]
print('baseline days count:', base.shape[0])  # expect 4018
bdates=[d for d in all_dates if dt.date(1992,1,1)<=d<=dt.date(2002,12,31)]
print('baseline date range', bdates[0], bdates[-1])
fin_base = np.isfinite(base).sum(axis=0)
print('baseline finite count per cell: min', fin_base.min(), 'max', fin_base.max())
# how many cells have ANY NaN in baseline among sea cells
print('sea cells with some baseline NaN:', ((fin_base < base.shape[0]) & finite_all).sum())
# distribution of finite counts among sea cells
import collections
vals, cnts = np.unique(fin_base[finite_all], return_counts=True)
print('finite-count histogram (sea cells):', list(zip(vals.tolist(), cnts.tolist()))[:20])
# fraction NaN in target per sea cell
tnan = (~np.isfinite(target)).sum(axis=0)[finite_all]
print('target NaN counts among sea cells: min', tnan.min(), 'max', tnan.max())
