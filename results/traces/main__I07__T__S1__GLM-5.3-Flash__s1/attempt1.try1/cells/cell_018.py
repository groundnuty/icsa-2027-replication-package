import numpy as np, xarray as xr, datetime as dt, json, fsspec, os, shutil
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# dataset coords for the region (as stored, float32)
with fs.open(f"{base}/sst_20210601.nc",'rb') as f:
    dsref = xr.open_dataset(f, engine="h5netcdf")
lat_r = dsref.latitude.values[48:108].copy()
lon_r = dsref.longitude.values[353:413].copy()
dsref.close()
print("lat_r[0], lat_r[-1]:", lat_r[0], lat_r[-1], "| lon_r[0], lon_r[-1]:", lon_r[0], lon_r[-1])

mhw = np.load('/tmp/mhw_result.npz')['mhw']          # (92, 3292) over sea cells
sea = np.load('/tmp/thr_clim.npz')['sea']            # (60,60) bool
T = mhw.shape[0]
mhw_grid = np.zeros((T, 60, 60), dtype=np.uint8)
mhw_grid[:, sea] = mhw.astype(np.uint8)
times = np.arange('2021-06-01', '2021-09-01', dtype='datetime64[D]').astype('datetime64[ns]')
assert times.shape[0] == T

dsout = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_grid, {"long_name": "marine heatwave (per-cell) mask", "flag_values": np.array([0,1],dtype=np.uint8), "flag_meanings": "not_in_mhw in_mhw"})},
    coords={"time": times, "lat": ("lat", lat_r, {"standard_name":"latitude","units":"degrees_north"}),
            "lon": ("lon", lon_r, {"standard_name":"longitude","units":"degrees_east"})},
)
dsout["mhw"].encoding = {"dtype": "uint8", "_FillValue": None}
written = []
for outdir in ['/work/workspace/output', '/work/output', '/tmp/workspace/output']:
    try:
        os.makedirs(outdir, exist_ok=True)
        dsout.to_netcdf(os.path.join(outdir, 'mhw_mask.nc'), engine='netcdf4')
        written.append(outdir)
    except Exception as e:
        print("write fail", outdir, type(e).__name__, str(e)[:120])
print("nc written to:", written)

# report
events = [{"onset": "2021-06-01", "end": "2021-08-08"}]
report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": events,
    "complete": True,
    "caveats": "",
}
for outdir in written:
    with open(os.path.join(outdir, 'report.json'), 'w') as fh:
        json.dump(report, fh, indent=2)
    print("report written:", outdir)
