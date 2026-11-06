import numpy as np, xarray as xr, h5py, datetime as dt, json, os
D='/data/icsa2027_data_20261101T090944Z/s1z'
os.makedirs('output', exist_ok=True)

# coords from the dataset (region subset)
with h5py.File(f'{D}/sst_20040601.nc','r') as f:
    lat=f['latitude'][34:94].astype(np.float32)
    lon=f['longitude'][213:273].astype(np.float32)

t64=np.arange(np.datetime64('2004-06-01'), np.datetime64('2004-09-01'), np.timedelta64(1,'D')).astype('datetime64[ns]')
print("time:", t64[0], t64[-1], t64.shape)

mhw=np.load('/tmp/mhw.npy')  # (92,60,60) bool, all False
mhw_u8=mhw.astype(np.uint8)
print("mhw sum:", int(mhw_u8.sum()))

ds=xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw_u8, {
        "long_name": "marine heatwave mask (per-cell MHW)",
        "flag_values": np.array([0,1],dtype=np.uint8),
        "flag_meanings": "not_in_mhw in_mhw",
        "units": "1"})},
    coords={"time": t64, "lat": ("lat", lat, {"units":"degrees_north","standard_name":"latitude","axis":"Y"}),
            "lon": ("lon", lon, {"units":"degrees_east","standard_name":"longitude","axis":"X"})})
ds["mhw"].encoding["dtype"]="u1"
ds.to_netcdf('output/mhw_mask.nc', engine='netcdf4')
print("wrote output/mhw_mask.nc", os.path.getsize('output/mhw_mask.nc'), "bytes")

report={
  "region": {"lat_min": 54.17, "lat_max": 55.37, "lon_min": 13.25, "lon_max": 14.45},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
  "events": [],
  "complete": True,
  "caveats": ("No marine heatwaves detected in the region over 2004-06-01..2004-08-31: SST exceeded the "
              "smoothed 90th-percentile threshold on 117 cell-days (peak 75 cells on 2004-08-01), but the "
              "longest consecutive hot run in any sea cell was 2 days, below the 5-day MHW minimum, so no "
              "per-cell MHW and no regional event exists; mhw mask is all zeros. Baseline climatology/"
              "threshold pools use the specified +/-5-day windows, which extend the days actually read to "
              "1991-12-27..2003-01-05 (nominal baseline years 1992-2002). Thresholds use the Hazen "
              "(Hyndman-Fan type 5) quantile as specified; all computations in float64; input data "
              "verified value-by-value against fresh reads.")
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json", os.path.getsize('output/report.json'), "bytes")
