
sub = ds.analysed_sst.sel(time=slice('1991-12-27','2005-08-31')).isel(latitude=la, longitude=lo).load()
print(sub.shape)
A = sub.values.astype(np.float64)
t = sub.time.values
tgt = (t>=np.datetime64('2005-06-01'))&(t<=np.datetime64('2005-08-31'))
print(tgt.sum(), np.isnan(A[tgt]).any(axis=0).sum(), (~np.isnan(A[tgt]).any(axis=0)).sum(), np.isnan(A).all(axis=0).sum())
