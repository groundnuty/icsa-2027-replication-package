import numpy as np, pandas as pd, json, os
import xarray as xr

os.makedirs("output", exist_ok=True)
maskA = np.load("work/maskA.npy").astype(np.uint8)
sea = np.load("work/sea.npy")
z = np.load("work/data.npz")
targ_dates = pd.DatetimeIndex(z["targ_dates"].astype(str))
latv = z["lat"]; lonv = z["lon"]

assert maskA.dtype == np.uint8
assert maskA[:, ~sea].sum() == 0          # land cells are 0
nt = maskA.shape[0]

# count per-cell MHWs after joining
def runs_1d(h):
    out, i, n = [], 0, len(h)
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]: j += 1
            out.append((i, j)); i = j+1
        else: i += 1
    return out
n_mhw = sum(len(runs_1d(maskA[:, i, j].astype(bool))) for i in range(60) for j in range(60) if sea[i, j])
print("per-cell MHWs (after joining):", n_mhw, "| active days:", int(maskA.any(axis=(1,2)).sum()))

# ---- regional events from the mask (final authority) ----
active = maskA.reshape(nt, -1).max(axis=1).astype(bool)
events = []
k = 0
while k < nt:
    if active[k]:
        l = k
        while l+1 < nt and active[l+1]: l += 1
        events.append((targ_dates[k], targ_dates[l])); k = l+1
    else: k += 1
for a, b in events: print("event:", a.date(), "->", b.date())

# ---- write mhw_mask.nc ----
ds = xr.Dataset(
    data_vars={"mhw": (("time", "lat", "lon"), maskA,
                       {"long_name": "marine heatwave per-cell mask (1 = cell inside a per-cell MHW)",
                        "units": "1", "flag_values": np.array([0, 1], dtype=np.uint8),
                        "flag_meanings": "not_in_mhw in_mhw"})},
    coords={"time": ("time", targ_dates.values, {"standard_name": "time"}),
            "lat":  ("lat", latv.astype(np.float32), {"standard_name": "latitude", "units": "degrees_north"}),
            "lon":  ("lon", lonv.astype(np.float32), {"standard_name": "longitude", "units": "degrees_east"})},
    attrs={"title": "Marine heatwave per-cell mask, Baltic Sea region, 2007-06-01 to 2007-08-31",
           "dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016)",
           "region": "lat 59.93-61.13 N, lon 18.69-19.89 E (bounds inclusive)",
           "baseline": "1992-2002; +/-5 calendar-day windows per day-of-year (overhang 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 included)",
           "threshold": "90th percentile of pool, Hazen (Hyndman-Fan type 5), 31-day circular moving mean; day 60 filled from days 59 and 61 before smoothing",
           "mhw_definition": "run of >=5 consecutive days with SST >= cell threshold; per-cell MHWs separated by 1-2 non-hot days joined",
           "sea_cells": "cells with finite SST on every target day",
           "history": "computed from /data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"})
enc = {"mhw": {"dtype": "uint8", "_FillValue": None, "zlib": True, "complevel": 4},
       "time": {"units": "days since 1982-01-01 00:00:00", "calendar": "proleptic_gregorian"},
       "lat": {"_FillValue": None}, "lon": {"_FillValue": None}}
ds.to_netcdf("output/mhw_mask.nc", engine="h5netcdf", encoding=enc)
print("wrote output/mhw_mask.nc", os.path.getsize("output/mhw_mask.nc"), "bytes")

# ---- write report.json ----
report = {
    "region": {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2007-06-01", "end": "2007-08-31"},
    "events": [{"onset": a.strftime("%Y-%m-%d"), "end": b.strftime("%Y-%m-%d")} for a, b in events],
    "complete": True,
    "caveats": ("Baseline years are 1992-2002; per day-of-year the +/-5 calendar-day windows reach "
                "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 and those days' SST values are included in "
                "the pools as the method specifies, so baseline_analysed reports the full span of baseline "
                "data actually used. Region bounds inclusive; the selected 60x60 grid block has float32 "
                "coordinates lat 59.94..61.12, lon 18.70..19.88 (neighbouring cells fall outside the bounds); "
                "3302 of 3600 cells are sea cells (finite SST on every target day), land cells are 0. Per-cell "
                "joining was applied to runs of >=5 hot days as worded in the method; joining all short runs "
                "first would enlarge the per-cell mask but yields identical regional events. Climatology was "
                "computed as specified but plays no role in the threshold-only detection. All statistics in "
                "float64; SST compared in kelvin as stored.")
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")
print(json.dumps({k: report[k] for k in ("region", "baseline_analysed", "target_analysed", "events", "complete")}, indent=1))
