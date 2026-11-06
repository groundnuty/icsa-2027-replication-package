
import xarray as xr, numpy as np, pandas as pd
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
sub=ds.sel(latitude=slice(58.69,59.89),longitude=slice(18.69,19.89))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
tg=sub.analysed_sst.sel(time=slice('2010-06-01','2010-08-31')).load()
print(b.dtype, np.nanmin(b.values), np.nanmax(b.values), np.isnan(b.values).mean())
print(np.nanmin(tg.values), np.nanmax(tg.values), np.isnan(tg.values).mean())
fin=np.isfinite(tg.values).all(axis=0); print('sea cells', fin.sum(), 'of', fin.size)
print('NaN per cell range', np.isnan(tg.values).sum(axis=0).min(), np.isnan(tg.values).sum(axis=0).max())
