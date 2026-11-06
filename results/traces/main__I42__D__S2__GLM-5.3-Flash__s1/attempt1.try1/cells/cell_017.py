import numpy as np, pandas as pd, xarray as xr, json, os, h5py

os.makedirs('output', exist_ok=True)
z = np.load('/work/final.npz')
per_cell = z['per_cell']           # (92,60,60) bool
tgt_dates = pd.read_pickle('/work/tgt_dates.pkl')
f = h5py.File('/work/sst_s2.nc','r')
LAT = f['latitude'][438:498].astype(np.float32)   # 62.26 .. 63.44
LON = f['longitude'][487:547].astype(np.float32)  # 18.74 .. 19.92

mhw = per_cell.astype(np.uint8)
assert mhw.dtype == np.uint8 and mhw.shape == (92,60,60)

ds_out = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw)},
    coords={"time": ("time", tgt_dates.values),
            "lat": ("lat", LAT),
            "lon": ("lon", LON)},
)
ds_out["mhw"].attrs = {"long_name": "marine heatwave mask (1 = cell inside a per-cell MHW that day)",
                       "flag_values": np.array([0,1],dtype=np.uint8), "flag_meanings": "not_in_mhw in_mhw"}
ds_out.attrs = {"title": "Per-cell marine heatwave mask, Baltic Sea region (62.25-63.45N, 18.73-19.93E)",
                "source": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP, DMI), file sst_s2.nc",
                "method": "90th-percentile threshold & mean climatology from 1992-2002 baseline (pools = +/-5 calendar days per day of year, hazen/linear type-5 percentile, day 60 filled from days 59&61, unweighted centred 31-day circular moving mean); hot day = SST >= threshold; per-cell MHW = >=5 consecutive hot days, gaps of 1-2 days joined; regional day active if any sea cell in MHW.",
                "history": "created by automated MHW analysis"}
enc = {"mhw": {"dtype": "uint8", "zlib": True},
       "time": {"units": "days since 2012-06-01 00:00:00", "calendar": "proleptic_gregorian"},
       "lat": {"dtype": "float32"}, "lon": {"dtype": "float32"}}
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)

# verify written file
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "| dims:", chk['mhw'].dims, "| shape:", chk['mhw'].shape)
print("time:", chk['time'].values[0], "->", chk['time'].values[-1], "n=", chk['time'].size)
print("lat:", float(chk['lat'][0]), "->", float(chk['lat'][-1]), "lon:", float(chk['lon'][0]), "->", float(chk['lon'][-1]))
print("mhw==1 cells:", int(chk['mhw'].values.sum()), "| days with any mhw:", int((chk['mhw'].values.sum(axis=(1,2))>0).sum()))
chk.close()

regional = json.load(open('/work/regional.json'))
report = {
    "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": tgt_dates.iloc[s].date().isoformat(),
                "end":   tgt_dates.iloc[e].date().isoformat()} for s, e in regional],
    "complete": True,
    "caveats": ("Region bounds snap to the dataset's ~0.02-degree grid: analysed cells span lat 62.26-63.44N, lon 18.74-19.92E (60x60 cells, 3308 sea cells, i.e. cells with finite SST on all 92 target days). "
                "Threshold/climatology pools cover the full prescribed 1992-2002 baseline plus the +/1-5-day edge windows, so SST from 1991-12-27 to 2003-01-05 was actually used (121 values per pool, all finite on sea cells). "
                "Hot-day comparison uses kelvin SST as stored; percentile is Hazen (Hyndman-Fan type 5) in float64; smoothing is an unweighted centred 31-day mean wrapping modulo 366 days. "
                "One regional event found: 2012-08-15 to 2012-08-19, with the same 26 cells in per-cell MHW on each of the 5 days; no other cell reached 5 consecutive hot days in the target period.")
}
with open('output/mhw_report.json','w') as fh:
    json.dump(report, fh, indent=2)
print(json.dumps({k: report[k] for k in ['region','baseline_analysed','target_analysed','events','complete']}, indent=1))
