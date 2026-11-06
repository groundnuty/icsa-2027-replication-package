import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
var = ds["analysed_sst"]
print("attrs:", dict(var.attrs))
print("encoding:", var.encoding)

# Region selection
lat = ds["latitude"].values
lon = ds["longitude"].values
lat_sel = (lat >= 57.85 - 1e-9) & (lat <= 59.05 + 1e-9)
lon_sel = (lon >= 21.01 - 1e-9) & (lon <= 22.21 + 1e-9)
print("n lat:", lat_sel.sum(), "n lon:", lon_sel.sum())
print("lats:", lat[lat_sel][:5], "...", lat[lat_sel][-3:])
print("lons:", lon[lon_sel][:5], "...", lon[lon_sel][-3:])

t = ds["time"].values
print("time range:", t[0], t[-1], "n:", len(t))
# check a slice of time values
import pandas as pd
print(pd.to_datetime(t[:5]), pd.to_datetime(t[-5:]))
