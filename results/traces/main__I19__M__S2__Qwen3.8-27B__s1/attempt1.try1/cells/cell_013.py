import xarray as xr
import numpy as np
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds.analysed_sst.attrs)
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
time = ds.time.values
print("lat range", lat.min(), lat.max(), "step", np.unique(np.diff(lat)))
print("lon range", lon.min(), lon.max(), "step", np.unique(np.diff(lon)))
# region selection with tolerance
tol = 1e-6
m_lat = (lat >= 57.13 - tol) & (lat <= 58.33 + tol)
m_lon = (lon >= 22.79 - tol) & (lon <= 23.99 + tol)
rlat = lat[m_lat]; rlon = lon[m_lon]
print("n lat", m_lat.sum(), rlat[0], rlat[-1])
print("n lon", m_lon.sum(), rlon[0], rlon[-1])
# check neighboring values just outside bounds
i0 = np.where(m_lat)[0][0]; i1 = np.where(m_lat)[0][-1]
print("lat around:", lat[i0-1:i1+2])
j0 = np.where(m_lon)[0][0]; j1 = np.where(m_lon)[0][-1]
print("lon around:", lon[j0-1:j1+2])
# time check
import pandas as pd
td = pd.to_datetime(time)
print("time first/last", td[0], td[-1], "len", len(td))
# check daily continuity
deltas = np.diff(time.astype('datetime64[D]').astype(np.int64))
print("unique day diffs:", np.unique(deltas))
