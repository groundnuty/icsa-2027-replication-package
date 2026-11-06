import os, datetime as dt, numpy as np, xarray as xr
base = "/data/icsa2027_data_20261101T090944Z/s1z"
names = sorted(os.listdir(base))
dates = [dt.date(int(n[4:8]), int(n[8:10]), int(n[10:12])) for n in names]
d0, d1 = dates[0], dates[-1]
alld = [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
missing = sorted(set(alld) - set(dates))
extra = sorted(set(dates) - set(alld))
print("range:", d0, d1, "n:", len(dates), "missing:", missing, "extra:", extra)

ds = xr.open_dataset(os.path.join(base, "sst_20130601.nc"), engine="h5netcdf")
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
print("lat:", lat[0], lat[-1], "step:", np.diff(lat)[:3], "n:", len(lat))
print("lon:", lon[0], lon[-1], "step:", np.diff(lon)[:3], "n:", len(lon))
sst = ds.analysed_sst
print("units:", sst.attrs.get("units"), "| valid_min:", sst.attrs.get("valid_min"), sst.attrs.get("valid_max"), "| dtype:", sst.dtype)
print("encoding:", {k: sst.encoding.get(k) for k in ("scale_factor","add_offset","_FillValue","dtype")})
print("time:", ds.time.values)

# region indices: cells with lat in [57.85,59.05], lon in [21.01,22.21] (inclusive), using stored values
latm = (lat >= 57.85) & (lat <= 59.05)
lonm = (lon >= 21.01) & (lon <= 22.21)
lati = np.where(latm)[0]; loni = np.where(lonm)[0]
print("lat idx:", lati[0], "..", lati[-1], "n=", lati.size, "vals:", lat[lati[0]], lat[lati[-1]])
print("lon idx:", loni[0], "..", loni[-1], "n=", loni.size, "vals:", lon[loni[0]], lon[loni[-1]])
# neighbours just outside
print("outside: lat", lat[lati[0]-1], lat[lati[-1]+1], " lon", lon[loni[0]-1], lon[loni[-1]+1])
