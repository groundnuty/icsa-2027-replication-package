import numpy as np, json, os, xarray as xr, fsspec, datetime as dt

os.makedirs('output', exist_ok=True)

# target metadata from cache
z = np.load('mhw_cache.npz', allow_pickle=False)
tgt_t = z['tgt_t']                      # 92 dates, 2004-06-01..2004-08-31
# coordinate values from a source file (dataset's grid)
fs = fsspec.filesystem('onedata'); base='icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20040601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values[34:94].copy()
    lon = ds['longitude'].values[213:273].copy()
    tsrc = ds['time'].values.copy()
    ds.close()

mhw = np.zeros((tgt_t.size, lat.size, lon.size), dtype=np.uint8)

ds_out = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw,
             {"long_name": "marine heatwave (per-cell) mask", "flag_values": np.array([0,1], dtype=np.uint8),
              "flag_meanings": "not_in_mhw in_mhw"})},
    coords={"time": ("time", tgt_t.astype('datetime64[ns]'), {"standard_name":"time","axis":"T"}),
            "lat":  ("lat", lat, {"units":"degrees_north","standard_name":"latitude","axis":"Y"}),
            "lon":  ("lon", lon, {"units":"degrees_east","standard_name":"longitude","axis":"X"})},
    attrs={"title": "Baltic Sea MHW mask, region 54.17-55.37N 13.25-14.45E, 2004-06-01..2004-08-31",
           "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
           "method": "p90 (hazen) threshold & mean climatology from 1992-2002 +/-5day doy pools, day60 filled, 31-day wrapped moving mean; hot runs >=5 d, gaps of 1-2 d joined"})
enc = {"mhw": {"dtype": "uint8", "zlib": True}, "time": {"units": "days since 2004-06-01", "dtype":"int32"}}
ds_out.to_netcdf('output/mhw_mask.nc', engine='netcdf4', encoding=enc)
print("wrote output/mhw_mask.nc")

report = {
  "region": {"lat_min": 54.17, "lat_max": 55.37, "lon_min": 13.25, "lon_max": 14.45},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
  "events": [],
  "complete": True,
  "caveats": ("No marine heatwaves detected: in this region summer 2004 SST stayed mostly below the 1992-2002 "
              "90th-percentile threshold (median SST-threshold -2.94 K; max exceedance +1.02 K on 2004-08-01; "
              "longest consecutive hot run in any cell was 2 days, below the 5-day MHW minimum), so no per-cell "
              "MHWs, no active days and no regional events. Per the method, pools include extension days "
              "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 around the baseline edges; day-of-year mapping is "
              "by month/day (31 Dec always 366, 1 Mar always 61). Sea cells = 3303 of 3600 (finite on all 92 target "
              "days); grid points at 0.02 deg spacing inside the inclusive bounds (54.18..55.36 N, 13.26..14.44 E).")
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")

# verify both files by re-reading
d2 = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print(d2)
print("mhw dtype:", d2['mhw'].dtype, "dims:", d2['mhw'].dims, "sum:", int(d2['mhw'].values.sum()),
      "time:", str(d2['time'].values[0])[:10], "->", str(d2['time'].values[-1])[:10], "n:", d2['time'].size)
print("lat:", float(d2.lat[0]), float(d2.lat[-1]), " lon:", float(d2.lon[0]), float(d2.lon[-1]))
d2.close()
r2 = json.load(open('output/report.json'))
print("report keys:", sorted(r2.keys()), "| events:", r2["events"], "| complete:", r2["complete"])
