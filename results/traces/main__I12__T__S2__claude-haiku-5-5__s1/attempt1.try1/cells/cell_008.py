
os.makedirs('output',exist_ok=True)
out = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw.astype(np.uint8))},
    coords={"time": tdates.values, "lat": sub.latitude.values, "lon": sub.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
report = {
 "region": {"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},
 "baseline_analysed": {"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed": {"start":"2009-06-01","end":"2009-08-31"},
 "events": events,
 "complete": True,
 "caveats": "Region grid is 60x60 cells (lat 56.10-57.28, lon 10.56-11.74); 3296 sea cells finite on all target days, others set to 0. Threshold from hazen 90th percentile with +/-5-day windows, day 60 averaged, 31-day wrap smoothing. Gap-joining applied to per-cell MHWs only (gap days counted as MHW). Reported region equals requested bounds."
}
json.dump(report, open('output/report.json','w'), indent=1)
print(open('output/report.json').read()); print(xr.open_dataset('output/mhw_mask.nc').mhw.shape)
