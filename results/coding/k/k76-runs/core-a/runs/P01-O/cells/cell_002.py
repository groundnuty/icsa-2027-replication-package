import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 64.51, 65.71
LON_MIN, LON_MAX = 21.97, 23.17
T_START = dt.date(2019, 6, 1)
T_END = dt.date(2019, 8, 31)
TOL = 1e-4

P = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
T0 = dt.date(1982, 1, 1)
YEARS = list(range(1992, 1997))  # 11 years of reads is slow for the time cap, use the first 5
one = dt.timedelta(days=1)

ds = xr.open_dataset(P, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
la = np.flatnonzero((lat >= LAT_MIN - TOL) & (lat <= LAT_MAX + TOL))
lo = np.flatnonzero((lon >= LON_MIN - TOL) & (lon <= LON_MAX + TOL))
sst = ds["analysed_sst"].isel(latitude=slice(la[0], la[-1] + 1), longitude=slice(lo[0], lo[-1] + 1))
print("region", len(la), "x", len(lo))

need = []
for y in YEARS:
    d = dt.date(y, 5, 12)
    while d <= dt.date(y, 9, 20):
        need.append(d)
        d += one
nb = len(need)
tdays = []
d = T_START
while d <= T_END:
    tdays.append(d)
    d += one
all_days = need + tdays
print("baseline days", nb, "target days", len(tdays))

spans = []
i = 0
while i < len(all_days):
    j = i
    while j + 1 < len(all_days) and (all_days[j + 1] - all_days[j]).days == 1:
        j += 1
    spans.append((i, j))
    i = j + 1
print(len(spans), "contiguous spans")

data = np.full((len(all_days), len(la), len(lo)), np.nan)
for n, (a, b) in enumerate(spans):
    ta = (all_days[a] - T0).days
    tb = (all_days[b] - T0).days
    data[a:b + 1] = sst.isel(time=slice(ta, tb + 1)).values
    print("span", n, all_days[a].isoformat(), all_days[b].isoformat())
np.save("sst_all.npy", data)
np.save("lat.npy", lat[la]); np.save("lon.npy", lon[lo])
meta = {"years": YEARS, "nb": nb, "days": [d.isoformat() for d in tdays],
        "baseline_start": need[0].isoformat(), "baseline_end": need[-1].isoformat()}
json.dump(meta, open("meta.json", "w"))
print("saved", data.shape)
