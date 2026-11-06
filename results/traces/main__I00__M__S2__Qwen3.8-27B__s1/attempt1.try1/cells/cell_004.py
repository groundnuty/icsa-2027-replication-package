import numpy as np, xarray
ds = xarray.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
sl = (lat >= 54.13) & (lat <= 55.33)
so = (lon >= 14.67) & (lon <= 15.87)

t = ds.time.values
i0 = np.where(t == np.datetime64("1991-12-27"))[0][0]
i1 = np.where(t == np.datetime64("2003-01-05"))[0][0]
j0 = np.where(t == np.datetime64("2004-06-01"))[0][0]
j1 = np.where(t == np.datetime64("2004-08-31"))[0][0]
print("indices:", i0, i1, j0, j1, "n_base_window:", i1-i0+1, "n_target:", j1-j0+1)

# load full needed span 1991-12-27 .. 2004-08-31 in one go (j1 >= i1)
S = ds.analysed_sst.values[i0:j1+1][sl][:, so].astype(np.float64)
print("S shape:", S.shape)  # (days, cells)
S = S.T  # (cells, days)
print("S (cells, days):", S.shape)
ncells, ndays = S.shape

# target slice: offset of j0 from i0
toff = j0 - i0
St = S[:, toff:j1+1-i0]  # (cells, 92)
nan_target = np.isnan(St).sum(axis=1)
sea = nan_target == 0
print("sea cells:", int(sea.sum()), "of", ncells)
print("cells with NaN in target: nan counts:", np.unique(nan_target[~sea], return_counts=True))
print("SST range in target (sea cells):", St[sea].min(), St[sea].max())

# baseline window NaNs for sea cells
Sb = S[:, :i1-i0+1]
nanbase = np.isnan(Sb).sum(axis=1)
print("sea cells with any NaN in base window:", int((nanbase[sea] > 0).sum()))
if (nanbase[sea] > 0).any():
    print("  counts:", np.unique(nanbase[sea][nanbase[sea]>0], return_counts=True))
# land cells: how many NaN in target
land = ~sea
print("land/nonsea cells:", int(land.sum()), "their nan counts in target:", np.unique(nan_target[land], return_counts=True)[:5])
print("sample land cell values:", S[land][0, :5])
print("sample sea cell values:", S[sea][0, toff:toff+5])
print("min SST overall region:", S.min(), "max:", S.max())
