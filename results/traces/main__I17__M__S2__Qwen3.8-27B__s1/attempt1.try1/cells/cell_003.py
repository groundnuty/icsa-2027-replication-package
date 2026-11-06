
import numpy as np, xarray as xr
print("numpy", np.__version__)
# sanity check of quantile methods on 1..10, p=0.9
x = np.arange(1, 11)
print("linear:", np.quantile(x, 0.9, method="linear"))
print("hazen :", np.quantile(x, 0.9, method="hazen"))
print("weibull:", np.quantile(x, 0.9, method="weibull"))

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
latm = (lat >= 56.63) & (lat <= 57.83)
lonm = (lon >= 20.23) & (lon <= 21.43)
i0, i1 = 3647, 7674   # 1991-12-27 .. 2003-01-05
j0, j1 = 10378, 10469 # 2010-06-01 .. 2010-08-31
bas = ds.analysed_sst.isel(time=sl(i0, i1+1)).values.astype("float64")
tgt = ds.analysed_sst.isel(time=sl(j0, j1+1)).values.astype("float64")
print("bas shape", bas.shape, "tgt shape", tgt.shape)
print("bas finite frac", np.isfinite(bas).mean(), "tgt finite frac", np.isfinite(tgt).mean())
sea2 = np.isfinite(tgt).all(axis=0)
print("n sea cells:", sea2.sum(), "of", sea2.size)
print("tgt SST range (sea):", np.nanmin(tgt[sea2]), np.nanmax(tgt[sea2]))
# how many target days are missing per non-sea cell (diagnostic)
miss = (~np.isfinite(tgt)).sum(axis=0)
print("non-sea cells:", (~sea2).sum(), "max missing days among them:", miss[~sea2].max() if (~sea2).any() else None)
# check NaN pattern of sea cells in baseline
si = np.argwhere(sea2)
Xb = bas[:, si[:,0], si[:,1]]
print("sea cells baseline finite frac:", np.isfinite(Xb).mean())
print("sea cells with any baseline NaN:", (np.isfinite(Xb).sum(axis=0) < Xb.shape[0]).sum())
import pickle
pickle.dump((bas, tgt, lat, lon, latm, lonm), open("/tmp/warm.pkl","wb"))
print("saved")
