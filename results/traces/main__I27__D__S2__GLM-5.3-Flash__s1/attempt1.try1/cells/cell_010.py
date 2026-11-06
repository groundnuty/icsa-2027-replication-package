import numpy as np, xarray as xr, json, os

os.makedirs('/work/output', exist_ok=True)

# exact coordinate values from the dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = ds.time.values
tmask = (t_all >= np.datetime64('2008-06-01')) & (t_all <= np.datetime64('2008-08-31'))
time_vals = t_all[tmask]                                   # 92 daily stamps
lat_vals = ds.latitude.values[217:277]                     # float32, 57.84..59.02
lon_vals = ds.longitude.values[421:481]                    # float32, 17.42..18.60

res = np.load('/work/mhw_result.npz')
mask = res['mask'].astype(np.uint8).reshape(len(time_vals), 60, 60)
assert mask.dtype == np.uint8 and mask.shape == (92, 60, 60)

out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mask,
             {"long_name": "per-cell marine heatwave mask (1 = inside per-cell MHW)",
              "units": "1", "flag_values": np.array([0, 1], dtype=np.uint8),
              "flag_meanings": "not_in_mhw in_mhw"})},
    coords={"time": ("time", time_vals, {"long_name": "Time", "standard_name": "time"}),
            "lat": ("lat", lat_vals, {"long_name": "latitude", "units": "degrees_north",
                                      "standard_name": "latitude"}),
            "lon": ("lon", lon_vals, {"long_name": "longitude", "units": "degrees_east",
                                      "standard_name": "longitude"})},
)
out["mhw"].encoding = {"dtype": "uint8"}
out.to_netcdf('/work/output/mhw_mask.nc')

# verify written file
chk = xr.open_dataset('/work/output/mhw_mask.nc')
print('mhw dtype:', chk.mhw.dtype, 'dims:', chk.mhw.dims, 'shape:', chk.mhw.shape)
print('time:', str(chk.time.values[0])[:10], '->', str(chk.time.values[-1])[:10], len(chk.time))
print('lat:', float(chk.lat[0]), float(chk.lat[-1]), 'lon:', float(chk.lon[0]), float(chk.lon[-1]))
print('ones:', int(chk.mhw.values.sum()))
chk.close()

report = {
    "region": {"lat_min": 57.83, "lat_max": 59.03, "lon_min": 17.41, "lon_max": 18.61},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
    "events": [{"onset": "2008-06-01", "end": "2008-06-15"},
               {"onset": "2008-07-24", "end": "2008-08-03"}],
    "complete": True,
    "caveats": ("Per-cell MHWs are defined only over the target period (hot runs >=5 d, gaps of 1-2 d joined), "
                "as prescribed; no days outside 2008-06-01..2008-08-31 were used for run detection. "
                "Per the method, the +-5-day pools for baseline day-of-year windows extend up to 5 days beyond "
                "the 1992-2002 baseline (1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 were used); "
                "29 February values enter their calendar neighbours' pools and day 60 (29 Feb) is set to the mean "
                "of days 59 and 61 before smoothing. Threshold (hazen/type-5 90th percentile) and climatology "
                "(mean) were smoothed with a wrap-around centred 31-day moving mean over 366 day-of-year values. "
                "Land/undefined cells (306 of 3600; 3294 sea cells, finite on every target day) are masked 0. "
                "SST used as stored in the dataset (analysed_sst, kelvin, float64 arithmetic)."
               ),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(open('/work/output/report.json').read())
print('files:', os.listdir('/work/output'), os.path.getsize('/work/output/mhw_mask.nc'))
