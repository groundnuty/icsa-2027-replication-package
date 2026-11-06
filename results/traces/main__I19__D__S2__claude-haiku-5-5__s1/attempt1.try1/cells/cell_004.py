
sub=ds.analysed_sst.isel(latitude=ri,longitude=ci).load()
t=sub.time.values
print(t[0],t[-1],len(t))
X=sub.values.astype(np.float64)
tgt=(t>=np.datetime64('2014-06-01'))&(t<=np.datetime64('2014-08-31'))
print(tgt.sum())
finite_all_tgt=np.isfinite(X[tgt]).all(axis=0)
print('sea cells',finite_all_tgt.sum())
print('nan count in target per cell min/max', np.isnan(X[tgt]).sum(axis=0).min(), np.isnan(X[tgt]).sum(axis=0).max())
