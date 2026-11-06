
sub=ds.analysed_sst.isel(latitude=li,longitude=lj)
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2009-06-01','2009-08-31')).load()
print(b.shape,t.shape, b.time.values[0], b.time.values[-1], t.time.values[0], t.time.values[-1])
print(np.isnan(t.values).sum(), np.nanmin(t.values), np.nanmax(t.values))
