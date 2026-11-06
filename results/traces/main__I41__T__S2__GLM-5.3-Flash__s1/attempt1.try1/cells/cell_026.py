import numpy as np, datetime as dt, json, os
import fsspec, xarray as xr

fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat_full = ds['latitude'].values.astype(np.float64)
    lon_full = ds['longitude'].values.astype(np.float64)
    ilat = np.where((lat_full >= 61.57) & (lat_full <= 62.77))[0]
    ilon = np.where((lon_full >= 20.17) & (lon_full <= 21.37))[0]
lat = lat_full[ilat]; lon = lon_full[ilon]
print("region lat:", lat[0], "..", lat[-1], f"({len(lat)})", "| lon:", lon[0], "..", lon[-1], f"({len(lon)})")
np.save('work/lat.npy', lat); np.save('work/lon.npy', lon)

mhw_mask = np.load('work/mhw_mask.npy')
tdates = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
T = np.load('work/T.npy')
assert mhw_mask.shape == (92, len(lat), len(lon))

os.makedirs('output', exist_ok=True)
mhw_u8 = mhw_mask.astype(np.uint8)
# land cells -> 0 already (they can never be hot: SST NaN)
mhw_u8[:, ~np.isfinite(T).all(axis=0)] = 0
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_u8)},
    coords={"time": np.array([np.datetime64(d, 'ns') for d in tdates]),
            "lat": lat, "lon": lon},
)
enc = {"mhw": {"dtype": "uint8", "zlib": True, "_FillValue": None}}
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print("wrote output/mhw_mask.nc")

# regional events
active = mhw_mask.any(axis=(1,2))
idx = np.flatnonzero(active); brk = np.flatnonzero(np.diff(idx) > 1)
ss = np.concatenate([[idx[0]], idx[brk+1]]); ee = np.concatenate([idx[brk], [idx[-1]]])
events = [(int(a), int(b)) for a, b in zip(ss, ee)]
ev_list = [{"onset": tdates[a].isoformat(), "end": tdates[b].isoformat()} for a, b in events]

report = {
    "region": {"lat_min": 61.57, "lat_max": 62.77, "lon_min": 20.17, "lon_max": 21.37},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": ev_list,
    "complete": True,
    "caveats": ("Baseline years 1992-2002 per spec; window dates outside the baseline (1991-12-27..31, "
                "2003-01-01..05) were included as the +/-5-day windows require. Region grid cells are the "
                "60x60 cells with lat in [61.57, 62.77] and lon in [20.17, 21.37] (60 unique lat/lon values "
                "in bounds); 3308 of 3600 cells are sea cells (finite SST on every target day), the other 292 "
                "are all-NaN land and are 0 in the mask. 'baseline_analysed' reports the extended window "
                "dates actually used; the baseline years themselves are 1992-2002.")
}
with open('output/report.json', 'w') as f_:
    json.dump(report, f_, indent=2)
print("wrote output/report.json")
print(json.dumps({k: v for k, v in report.items() if k != 'caveats'}, indent=2))
