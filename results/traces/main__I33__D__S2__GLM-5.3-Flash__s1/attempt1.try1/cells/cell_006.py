import numpy as np
ext = np.load('/work/ext.npy'); tgt = np.load('/work/tgt.npy')
nan_e = np.isnan(ext).sum(axis=0); nan_t = np.isnan(tgt).sum(axis=0)
print('cells NaN in target:', (nan_t>0).sum(), ' cells NaN in baseline:', (nan_e>0).sum())
print('same mask:', np.array_equal(nan_e>0, nan_t>0))
print('sea cells (finite all target days):', (nan_t==0).sum())
# do any sea cells have NaNs in baseline?
sea = nan_t==0
print('max baseline NaN count among sea cells:', nan_e[sea].max())
print('baseline NaN counts distribution among sea cells:', np.unique(nan_e[sea]))
# sea cell fraction vs expected Baltic land
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values[278:338]; lon = ds.longitude.values[613:673]
print('lat range', lat[0], lat[-1], 'lon range', lon[0], lon[-1])
# count NaN per day for sea cells only
sea_nan_per_day = np.isnan(ext[:, sea]).sum(axis=1)
print('baseline NaN per day among sea cells: max', sea_nan_per_day.max(), 'days with any:', (sea_nan_per_day>0).sum())