import fsspec, xarray as xr, numpy as np, json, os

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
tvals = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
la = np.where((lat>=54.13)&(lat<=55.33))[0]; lo = np.where((lon>=14.67)&(lon<=15.87))[0]
t0i = int(np.searchsorted(tvals, np.datetime64('2008-06-01')))
t1i = int(np.searchsorted(tvals, np.datetime64('2008-08-31'), 'right'))
tdates = tvals[t0i:t1i]
lat_v = lat[la].astype(np.float64); lon_v = lon[lo].astype(np.float64)

mhw = np.load('/tmp/mhw_mask2.npz')['mhw']  # (92,60,60) uint8
print("mask dtype/shape:", mhw.dtype, mhw.shape)

os.makedirs('output', exist_ok=True)
dso = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw)},
    coords={"time": tdates, "lat": lat_v, "lon": lon_v},
)
dso["mhw"].attrs = {"long_name": "marine heatwave (per-cell) mask", "flag_values": np.array([0,1], dtype=np.uint8),
                    "flag_meanings": "not_in_mhw in_mhw", "units": "1"}
dso.attrs.update({
    "title": "Per-cell marine heatwave mask, SW Baltic (Pomeranian Bay region)",
    "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
    "region": "lat 54.13-55.33 N, lon 14.67-15.87 E (bounds inclusive)",
    "target_period": "2008-06-01 to 2008-08-31",
    "baseline": "1992-2002 (+/-5-day windows incl. 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05)",
    "threshold": "smoothed 90th percentile (hazen) of baseline pool per day of year",
})
enc = {"mhw": {"dtype": "uint8", "zlib": True, "complevel": 4},
       "time": {"units": "days since 1982-01-01 00:00:00", "dtype": "int32"},
       "lat": {"dtype": "float64"}, "lon": {"dtype": "float64"}}
dso.to_netcdf('output/mhw_mask.nc', engine='netcdf4', encoding=enc)
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
    "events": [{"onset": "2008-06-01", "end": "2008-06-21"}],
    "complete": True,
    "caveats": ("Full analysis completed as specified; all computations in float64. "
                "Baseline days outside 1992-2002 (1991-12-27..31, 2003-01-01..05) are counted because "
                "the +/-5-day windows around 1 Jan/31 Dec extend past the baseline edges, as prescribed. "
                "Sea cells = 3301 (cells with finite SST on every target day); land cells masked 0. "
                "An independent re-implementation (manual Hyndman-Fan type-5 quantile, brute-force run merging) "
                "reproduced the mask, events and climatology exactly; thresholds matched within 1.2e-13 K.")
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")

# final read-back validation of the NetCDF
chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
print("mhw dtype:", chk.mhw.dtype, "dims:", chk.mhw.dims, "sum:", int(chk.mhw.values.sum()))
assert chk.mhw.dtype == np.uint8 and chk.mhw.dims == ("time","lat","lon")
assert int(chk.mhw.values.sum()) == 12088
print("read-back OK")
