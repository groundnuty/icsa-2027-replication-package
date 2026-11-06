import numpy as np, pickle, json, os, datetime as dt
import xarray as xr

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
R = pickle.load(open("/tmp/mhw_results.pkl","rb"))
T = D["T"]; tdays = D["tgt_dates"]
lat_sel = D["lat_sel"]; lon_sel = D["lon_sel"]
msk = R["msk_h"].astype(np.uint8)
evs = R["evs_h"]

assert msk.shape == (92, 60, 60) and msk.dtype == np.uint8
assert set(np.unique(msk)) <= {0,1}
sea = np.all(np.isfinite(T), axis=0)
print("land cells with nonzero mhw:", int(((~sea) & (msk.sum(axis=0) > 0)).sum()))
tcoord = np.array([dt.datetime(d.year,d.month,d.day) for d in tdays], dtype="datetime64[ns]")
print("time:", tcoord[0], "..", tcoord[-1], "n=", len(tcoord))
print("events:", evs)

os.makedirs("output", exist_ok=True)
var = xr.DataArray(msk, dims=("time","lat","lon"),
                   coords={"time": tcoord, "lat": lat_sel.astype(np.float32), "lon": lon_sel.astype(np.float32)})
ds = xr.Dataset({"mhw": var})
ds.to_netcdf("output/mhw_mask.nc")
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.33, "lat_max": 58.53, "lon_min": 9.03, "lon_max": 10.23},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": a, "end": b} for a, b in evs],
    "complete": True,
    "caveats": ("No per-cell MHW was detected in this region over 2012-06-01..2012-08-31: no sea cell reached 5 consecutive "
                "days with SST >= its (smoothed) 90th-percentile threshold; the longest hot streak was 3 consecutive days. "
                "Closest near-miss: cell at 57.36N, 9.66E had hot days 2012-07-05/06 and 2012-07-08/09/10, split by 2012-07-07 "
                "which was 0.54 K below threshold, so no >=5-day MHW (and hence no regional event) formed. All 3314 sea cells "
                "(of 3600 grid cells) were finite on every target day and every baseline-window day (1991-12-27..2003-01-05), "
                "so no missing-value handling affected thresholds. Note: numpy 2.x method='hazen' (used as specified) differs "
                "by up to ~0.004 K from MATLAB's default 'linear' interpolation for these n=121 pools; the final mask and events "
                "were verified identical under both conventions. Data for the analysed periods were read from s2z/sst_s2.nc "
                "(covers 1982-01-01..2023-12-31); the s1z daily files only cover 1982-01-01..1984-09-26.")
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")