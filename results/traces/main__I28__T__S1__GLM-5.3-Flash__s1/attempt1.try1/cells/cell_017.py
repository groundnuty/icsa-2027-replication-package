import numpy as np, xarray as xr, json
print("numpy", np.__version__, "xarray", xr.__version__)
# check nanquantile method='hazen' support
a = np.array([1.,2,3,4,5,6,7,8,9,10, np.nan])
print("hazen q90:", np.nanquantile(a, 0.9, method='hazen'))
try:
    import h5netcdf; print("h5netcdf", h5netcdf.__version__)
except Exception as e: print("h5netcdf ERR", e)
try:
    import netCDF4; print("netCDF4", netCDF4.__version__)
except Exception as e: print("netCDF4 missing")

# verify cache
data = np.load('/tmp/chunk1.npy')
print("chunk1:", data.shape, data.dtype)
lat = np.load('/tmp/latvals.npy'); lon = np.load('/tmp/lonvals.npy')
tvals = np.load('/tmp/tvals.npy')
print("lat range:", lat.min(), lat.max(), "lon range:", lon.min(), lon.max())
print("time first/last:", tvals[0], tvals[-1], "n:", len(tvals))
fin_per_day = np.isfinite(data).sum(axis=(1,2))
print("finite per day: min", fin_per_day.min(), "max", fin_per_day.max())
allnan_days = (fin_per_day==0).sum()
print("all-NaN days:", allnan_days)
# target block
print("target finite per day (last 92):", np.unique(np.isfinite(data[-92:]).sum(axis=(1,2))))
