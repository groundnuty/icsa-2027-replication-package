import h5py, numpy as np, pandas as pd
f = h5py.File('/work/sst_s2.nc','r')
t = f['time'][:]
secs = pd.to_timedelta(t, unit='s')
odd = ~(secs % pd.Timedelta('1D') == pd.Timedelta(0))
print("n odd:", int(odd.sum()))
if odd.sum():
    idx = np.where(odd)[0][:10]
    print(idx, secs[odd][:10])
dates = (pd.Timestamp('1981-01-01') + secs).normalize()
print("unique:", len(np.unique(dates.values)) == len(dates), "sorted:", bool((np.diff(dates.values) > pd.Timedelta(0)).all()))
