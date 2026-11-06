
sub = ds.analysed_sst.isel(latitude=la, longitude=lo).sel(time=slice('1991-12-27','2021-08-31')).load()
T = sub.time.values.astype('datetime64[D]')
A = sub.values.astype(np.float64)
print(A.shape, T[0], T[-1], np.isnan(A).sum(), np.nanmin(A), np.nanmax(A))
# check time continuity
print(np.unique(np.diff(T)))
