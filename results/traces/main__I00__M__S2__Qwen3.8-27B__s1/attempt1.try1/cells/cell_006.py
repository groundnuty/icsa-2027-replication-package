import numpy as np, xarray
ds = xarray.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
sl_idx = np.where((lat >= 54.13) & (lat <= 55.33))[0]
so_idx = np.where((lon >= 14.67) & (lon <= 15.87))[0]
print("n lat:", len(sl_idx), "n lon:", len(so_idx))

t = ds.time.values
i0 = int(np.where(t == np.datetime64("1991-12-27"))[0][0])
i1 = int(np.where(t == np.datetime64("2003-01-05"))[0][0])
j0 = int(np.where(t == np.datetime64("2004-06-01"))[0][0])
j1 = int(np.where(t == np.datetime64("2004-08-31"))[0][0])

sub = ds.analysed_sst.isel(time=slice(i0, j1+1), latitude=sl_idx, longitude=so_idx)
S = sub.values  # (days, nlat, nlon)
print("loaded:", S.shape, S.dtype)
S = S.reshape(S.shape[0], -1).T.astype(np.float64)  # (cells, days)
ncells, ndays = S.shape
print("(cells, days):", S.shape)

toff = j0 - i0
St = S[:, toff:j1+1-i0]
nan_target = np.isnan(St).sum(axis=1)
sea = nan_target == 0
print("sea cells:", int(sea.sum()), "of", ncells)
if (~sea).any():
    print("nonsea nan counts:", np.unique(nan_target[~sea], return_counts=True))
print("SST target range (sea):", St[sea].min(), St[sea].max())

Sb = S[:, :i1-i0+1]
nanbase = np.isnan(Sb).sum(axis=1)
nb = nanbase[sea]
print("sea cells with NaN in base window:", int((nb > 0).sum()))
if (nb > 0).any():
    print("  counts:", np.unique(nb[nb>0], return_counts=True))
land = ~sea
if land.any():
    print("nonsea cells:", int(land.sum()), "sample:", S[land][0, toff:toff+3])
print("overall min/max:", S.min(), S.max())
np.save("/tmp/S.npy", S)
print("saved /tmp/S.npy, shape", S.shape)
