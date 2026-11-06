import numpy as np, datetime as dt, json, os
import xarray as xr

os.makedirs('output', exist_ok=True)
mhw = np.load('/tmp/mhw_final.npy')   # (92,60,60) bool
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]

# dataset coordinate values for the region (from source grid, indices 192:252 / 2:62)
import fsspec, h5py
fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20210601.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        lat = hf['latitude'][192:252].astype(np.float32)
        lon = hf['longitude'][2:62].astype(np.float32)
assert len(lat) == 60 and len(lon) == 60

ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw.astype(np.uint8),
             {"long_name": "marine heatwave (per-cell MHW) mask", "flag_values": np.array([0,1],dtype=np.uint8),
              "flag_meanings": "not_in_mhw in_mhw"})},
    coords={"time": ("time", np.array([np.datetime64(d) for d in tgt_days], dtype='datetime64[ns]')),
            "lat": ("lat", lat, {"units":"degrees_north","standard_name":"latitude"}),
            "lon": ("lon", lon, {"units":"degrees_east","standard_name":"longitude"})},
    attrs={"title": "Baltic Sea MHW mask (per-cell), region 57.33-58.53N 9.03-10.23E, 2021-06-01..2021-08-31",
           "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
           "method": "threshold = 90th percentile (hazen/type-5) of +/-5-day window pools over 1992-2002 baseline, 31-day wrapped moving mean; climatology = window-pool mean, same smoothing; hot: SST >= threshold; MHW: >=5 hot days, gaps of 1-2 days joined"})
enc = {"mhw": {"dtype": "uint8", "zlib": True},
       "time": {"units": "days since 1981-01-01", "dtype": "int64"},
       "lat": {"dtype": "float32"}, "lon": {"dtype": "float32"}}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.33, "lat_max": 58.53, "lon_min": 9.03, "lon_max": 10.23},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": "2021-06-19", "end": "2021-06-25"},
               {"onset": "2021-06-30", "end": "2021-07-29"}],
    "complete": True,
    "caveats": ""
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")
print(json.dumps(report, indent=2))
