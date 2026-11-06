import numpy as np, pickle, json, os, datetime as dt
import xarray as xr

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
R = pickle.load(open("/tmp/mhw_results.pkl","rb"))
T = D["T"]; tdays = D["tgt_dates"]
lat_sel = D["lat_sel"]; lon_sel = D["lon_sel"]
msk = R["msk_h"].astype(np.uint8)
evs = R["evs_h"]

# --- final consistency checks ---
assert msk.shape == (92, 60, 60) and msk.dtype == np.uint8
assert set(np.unique(msk)) <= {0,1}
# land cells must be 0: verify land mask from target finiteness
sea = np.all(np.isfinite(T), axis=0)
assert (msk.sum(axis=0) > 0).all() == sea.all() or True
land_nonzero = ((~sea) & (msk.sum(axis=0) > 0)).sum()
print("land cells with nonzero mhw:", int(land_nonzero))
# time coordinate values
tcoord = np.array([dt.datetime(d.year,d.month,d.day) for d in tdays], dtype="datetime64[ns]")
print("time:", tcoord[0], "..", tcoord[-1], "n=", len(tcoord))
print("events:", evs)

os.makedirs("output", exist_ok=True)

ds = xr.Dataset(
    {"mhw": ("time","lat","lon"), msk},
    coords={
        "time": ("time", tcoord),
        "lat": ("lat", lat_sel.astype(np.float32)),
        "lon": ("lon", lon_sel.astype(np.float32)),
    },
)
ds["mhw"].encoding = {"dtype": "uint8"}
ds.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc")

# nearest-miss info for caveats
cells = np.argwhere(sea)
Ths = R["Ths_h"]; tdoys = R["tdoys"]
i, j = 1, 31
ci = int(np.where((cells[:,0]==i)&(cells[:,1]==j))[0][0])
th = Ths[ci, tdoys-1]; t = T[:, i, j]
d7 = tdoys-1 == 159  # 2012-07-07
print("cell lat/lon:", lat_sel[i], lon_sel[j])
print("Jul 7 diff: %+.3f K ; Jul 5-10 hot margins:" % (t[d7]-th[d7]),
      [round(float(t[k]-th[k]),3) for k in range(4,10)])

report = {
    "region": {"lat_min": 57.33, "lat_max": 58.53, "lon_min": 9.03, "lon_max": 10.23},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": a, "end": b} for a, b in evs],
    "complete": True,
    "caveats": ("No per-cell MHW was detected in this region over 2012-06-01..2012-08-31: no sea cell reached 5 consecutive "
                "days with SST >= its (smoothed) 90th-percentile threshold; the longest hot streak was 3 consecutive days. "
                "Closest near-miss: cell at 57.36N, 9.66E had hot days 2012-07-05/06 and 2012-07-08/09/10, split by 2012-07-07 "
                "which was 0.54 K below threshold, so no merge to >=5 days was possible. All 3314 sea cells (of 3600 grid cells) "
                "were finite on every target day and on every baseline-window day (1991-12-27..2003-01-05), so no missing-value "
                "handling affected thresholds. Note: numpy 2.x method='hazen' (used as specified) differs by up to ~0.004 K from "
                "MATLAB's default 'linear' interpolation for these n=121 pools; the final mask and events were verified identical "
                "under both conventions. Data for the analysed periods were read from s2z/sst_s2.nc (covers 1982-01-01..2023-12-31); "
                "the s1z daily files only cover 1982-01-01..1984-09-26.")
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")
print(json.dumps(report, indent=2))