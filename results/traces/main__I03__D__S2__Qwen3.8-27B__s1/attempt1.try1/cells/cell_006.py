import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
t = ds.time.values
print("lat range:", lat.min(), lat.max(), "n=", len(lat))
print("lon range:", lon.min(), lon.max(), "n=", len(lon))
print("time first/last:", t[0], t[-1], "n=", len(t))

# check daily continuity
diffs = np.diff(t).astype('timedelta64[D]')
print("time diffs all == 1 day:", np.all(diffs == 1))

# region masks
m_lat = (lat >= 54.17) & (lat <= 55.37)
m_lon = (lon >= 13.25) & (lon <= 14.45)
print("n lat in region:", m_lat.sum(), "n lon in region:", m_lon.sum())
print("lats:", lat[m_lat][:5], "...", lat[m_lat][-5:])
print("lons:", lon[m_lon][:5], "...", lon[m_lon][-5:])

# units check: SST over region in June 2014
import pandas as pd
tidx = {pd.Timestamp(dt): i for i, dt in enumerate(t) if pd.Timestamp(dt) in (pd.Timestamp('2014-06-15'),)}
# simpler: find index via search
ti = np.searchsorted(t, np.datetime64('2014-06-15'))
print("t[ti] =", t[ti])
sl = ds.analysed_sst.isel(time=ti).values
reg = sl[np.ix_(m_lat, m_lon)]
print("2014-06-15 region: min", np.nanmin(reg), "max", np.nanmax(reg), "mean", np.nanmean(reg), "finite frac", np.isfinite(reg).mean())
