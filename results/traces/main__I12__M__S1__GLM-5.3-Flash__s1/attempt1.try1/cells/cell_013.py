import numpy as np, datetime as dt, os
dates = np.load('/tmp/dates.npy')
data = np.load('/tmp/sst_needed.npy')
print(dates[0], dates[-1], data.shape)
d0, d1 = dt.date(1991,12,27), dt.date(2003,1,5)
t0d, t1d = dt.date(2009,6,1), dt.date(2009,8,31)
n_base = sum(1 for d in dates if dt.date(d.astype(object).year, d.astype(object).month, d.astype(object).day) <= d1)
print('baseline-window days:', n_base, 'target days:', len(dates)-n_base)

# sea cells: finite on every target day
target = data[n_base:]
sea = np.isfinite(target).all(axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)
