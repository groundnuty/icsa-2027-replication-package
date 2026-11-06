import numpy as np, xarray as xr, sys
print("numpy", np.__version__, "xarray", xr.__version__)
import h5netcdf, netCDF4
print("h5netcdf", h5netcdf.__version__, "netCDF4", netCDF4.__version__)
try:
    import h5py; print("h5py", h5py.__version__)
except Exception as e:
    print("h5py missing", e)

p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120701.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
v = ds['analysed_sst']
print("encoding:", v.encoding)
print("chunks:", v.chunks if hasattr(v,'chunks') else None)
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat dtype", lat.dtype, "lon dtype", lon.dtype)
print("lat min/max", lat.min(), lat.max(), "lon min/max", lon.min(), lon.max())
latm = lat[np.logical_and(lat >= 60.09, lat <= 61.29)]
lonm = lon[np.logical_and(lon >= 20.01, lon <= 21.21)]
print("n lat in region:", len(latm), latm[:3], latm[-3:])
print("n lon in region:", len(lonm), lonm[:3], lonm[-3:])
print("finite values overall:", np.isfinite(v.values).mean())
ds.close()
