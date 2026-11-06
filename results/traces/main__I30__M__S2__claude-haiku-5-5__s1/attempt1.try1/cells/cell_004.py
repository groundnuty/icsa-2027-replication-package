
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
tg=sub.analysed_sst.sel(time=slice('2010-06-01','2010-08-31')).load()
print(b.dtype, np.nanmin(b.values), np.nanmax(b.values), np.isnan(b.values).mean())
print(np.nanmin(tg.values), np.nanmax(tg.values), np.isnan(tg.values).mean())
fin=np.isfinite(tg.values).all(axis=0); print('sea cells', fin.sum(), 'of', fin.size)
print('target NaN per cell range', np.isnan(tg.values).sum(axis=0).min(), np.isnan(tg.values).sum(axis=0).max())
