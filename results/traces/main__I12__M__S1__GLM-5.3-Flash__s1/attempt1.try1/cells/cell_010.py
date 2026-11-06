import os, pickle, numpy as np
DIR = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(DIR))
import datetime as _dt
dates = np.array([_dt.date(int(f[4:8]), int(f[8:10]), int(f[10:12])) for f in files])
np.save('/tmp/dates.npy', dates.astype('datetime64[D]'))
data = np.load('/tmp/all_sst.npy')
print(data.shape, data.dtype)
# per-cell finite counts over full record
fin_counts = np.isfinite(data).sum(axis=0)
print('finite count stats: min', fin_counts.min(), 'max', fin_counts.max())
# where are the non-finite cells? map
nfin = (fin_counts < data.shape[0])
print('cells with any gap (over full record):', nfin.sum())
