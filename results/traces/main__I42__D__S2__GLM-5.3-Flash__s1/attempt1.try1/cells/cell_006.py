import h5py, numpy as np, pandas as pd, time

f = h5py.File('/work/sst_s2.nc','r')
t = f['time'][:]
dates = (pd.Timestamp('1981-01-01') + pd.to_timedelta(t, unit='s')).normalize()
print("dates:", dates[0], dates[-1], "n=", len(dates))
# check all midnights / unique
print("all midnight:", bool((pd.to_timedelta(t, unit='s') % 86400 == 0).all()))

d = f['analysed_sst']
# target indices
tgt_mask = (dates >= '2012-06-01') & (dates <= '2012-08-31')
tgt_idx = np.where(tgt_mask)[0]
print("target n =", tgt_idx.size, dates[tgt_idx[0]], dates[tgt_idx[-1]])
# baseline extended indices
base_mask = (dates >= '1991-12-27') & (dates <= '2003-01-05')
base_idx = np.where(base_mask)[0]
print("baseline ext n =", base_idx.size, dates[base_idx[0]], dates[base_idx[-1]])

# benchmark: read 30 target days
t0 = time.time()
sub = d[tgt_idx[:30].tolist(), 438:498, 487:547]
dt = time.time() - t0
print("30 days read: %.2f s -> full 4120 days ~ %.1f min" % (dt, dt/30*4120/60))
print(sub.dtype, sub.shape)
