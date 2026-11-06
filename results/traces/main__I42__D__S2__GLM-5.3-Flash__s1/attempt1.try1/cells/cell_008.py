import h5py, numpy as np, pandas as pd, time

f = h5py.File('/work/sst_s2.nc','r')
t = f['time'][:]
dates = (pd.Timestamp('1981-01-01') + pd.to_timedelta(t, unit='s')).normalize()
d = f['analysed_sst']

tgt_idx = np.where((dates >= '2012-06-01') & (dates <= '2012-08-31'))[0]
base_idx = np.where((dates >= '1991-12-27') & (dates <= '2003-01-05'))[0]
tgt_dates = dates[tgt_idx]
base_dates = dates[base_idx]
print("target:", tgt_dates[0], "->", tgt_dates[-1], "n=", len(tgt_idx))
print("baseline ext:", base_dates[0], "->", base_dates[-1], "n=", len(base_idx))

def read_days(idx, name):
    out = np.empty((len(idx), 60, 60), dtype=np.float32)
    t0 = time.time()
    for k, ii in enumerate(idx):
        out[k] = d[int(ii), 438:498, 487:547]
    print(f"{name}: read {len(idx)} days in {time.time()-t0:.1f}s, finite frac {np.isfinite(out).mean():.4f}")
    return out

sst_base = read_days(base_idx, 'baseline')
sst_tgt = read_days(tgt_idx, 'target')
np.save('/work/sst_base.npy', sst_base)
np.save('/work/sst_tgt.npy', sst_tgt)
base_dates.to_series().to_pickle('/work/base_dates.pkl')
tgt_dates.to_series().to_pickle('/work/tgt_dates.pkl')
print("saved")
