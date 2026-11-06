import os, time, json
import numpy as np, xarray as xr
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
os.makedirs("output", exist_ok=True)

# ---- Region indices from dataset coordinates ----
ds0 = xr.open_dataset(base + "/sst_20210601.nc", engine="h5netcdf")
lat = ds0['latitude'].values
lon = ds0['longitude'].values
lat_sel = np.where((lat >= 54.45) & (lat <= 55.65))[0]
lon_sel = np.where((lon >= 16.05) & (lon <= 17.25))[0]
print("lat idx", lat_sel.min(), lat_sel.max(), "n=", len(lat_sel))
print("lon idx", lon_sel.min(), lon_sel.max(), "n=", len(lon_sel))
print("lat range", lat[lat_sel.min()], lat[lat_sel.max()])
print("lon range", lon[lon_sel.min()], lon[lon_sel.max()])
print("time val sample:", ds0['time'].values)
ds0.close()

def daterange(d0, d1):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)

# ---- Load region SST for a list of dates ----
def load_region(dates, tag):
    out = np.empty((len(dates), len(lat_sel), len(lon_sel)), dtype=np.float64)
    times = np.empty(len(dates), dtype="datetime64[ns]")
    t0 = time.time()
    for i, d in enumerate(dates):
        p = f"{base}/sst_{d.year:04d}{d.month:02d}{d.day:02d}.nc"
        ds = xr.open_dataset(p, engine="h5netcdf")
        s = ds['analysed_sst'].isel(latitude=lat_sel, longitude=lon_sel).values
        times[i] = ds['time'].values[0]
        out[i] = s.astype(np.float64)
        ds.close()
        if (i+1) % 500 == 0:
            print(tag, "loaded", i+1, "/", len(dates), f"elapsed {time.time()-t0:.1f}s", flush=True)
    print(tag, "DONE", time.time()-t0, "s")
    return out, times

base_dates = list(daterange(date(1991,12,27), date(2003,1,5)))
tgt_dates  = list(daterange(date(2021,6,1), date(2021,8,31)))
print("n base dates:", len(base_dates), "n target dates:", len(tgt_dates))

B, btimes = load_region(base_dates, "baseline")
T, ttimes = load_region(tgt_dates, "target")
np.savez("/tmp/sst_data.npz", B=B, T=T,
         lat=lat[lat_sel], lon=lon[lon_sel],
         btimes=btimes, ttimes=ttimes)
print("saved /tmp/sst_data.npz", os.path.getsize("/tmp/sst_data.npz"))
print("B finite frac:", np.isfinite(B).mean(), "T finite frac:", np.isfinite(T).mean())
