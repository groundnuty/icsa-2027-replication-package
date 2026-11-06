script = '''
import numpy as np
import xarray as xr
import json, os

PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
OUT = '/work/output'
os.makedirs(OUT, exist_ok=True)

M = np.load('/work/mhw.npz', allow_pickle=True)
Z = np.load('/work/interim.npz', allow_pickle=True)
mem = M['mem']                     # (92, 3600)
tgt_dates = np.asarray(M['tgt_dates'], dtype=str)
rlat = Z['rlat']; rlon = Z['rlon']

ds = xr.open_dataset(PATH, engine="h5netcdf")
# region coordinates straight from the dataset (original dtype/values)
lat_all = ds.latitude; lon_all = ds.longitude
tol = 1e-6
mlat = (lat_all.values.astype(np.float64) >= 57.13 - tol) & (lat_all.values.astype(np.float64) <= 58.33 + tol)
mlon = (lon_all.values.astype(np.float64) >= 22.79 - tol) & (lon_all.values.astype(np.float64) <= 23.99 + tol)
rlat_ds = lat_all[mlat]
rlon_ds = lon_all[mlon]
assert len(rlat_ds) == 60 and len(rlon_ds) == 60
assert np.array_equal(rlat_ds.values.astype(np.float64), rlat)
assert np.array_equal(rlon_ds.values.astype(np.float64), rlon)

# target time slice from the dataset
t_all = ds.time
d0 = np.datetime64('2014-06-01'); d1 = np.datetime64('2014-08-31')
ti0 = int(np.searchsorted(t_all.values, d0)); ti1 = int(np.searchsorted(t_all.values, d1))
t_sel = t_all[ti0:ti1+1]
assert len(t_sel) == 92
assert np.array_equal(t_sel.values.astype('datetime64[D]').astype(str), np.array(tgt_dates))

mask = mem.reshape(92, 60, 60).astype(np.uint8)

out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mask)},
    coords={"time": t_sel, "lat": rlat_ds, "lon": rlon_ds},
)
out.attrs["description"] = ("Per-cell marine heatwave membership (1 = inside a per-cell MHW, "
                            "0 otherwise; land 0) for lat 57.13-58.33N, lon 22.79-23.99E, "
                            "2014-06-01..2014-08-31. Method: 1992-2002 baseline (windows +/-5 d), "
                            "Hazen 90th percentile threshold, 31-d centred smoothed (366-d wrap), "
                            "runs >=5 d, gaps of 1-2 d joined.")
out.mhw.attrs["flag_values"] = np.array([0, 1], dtype=np.uint8)
out.mhw.attrs["flag_meanings"] = "not_in_mhw in_mhw"
out.to_netcdf(os.path.join(OUT, "mhw_mask.nc"))
ds.close()

report = {
    "region": {"lat_min": 57.13, "lat_max": 58.33, "lon_min": 22.79, "lon_max": 23.99},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
    "events": [{"onset": "2014-07-24", "end": "2014-08-18"}],
    "complete": True,
    "caveats": ("Grid cells inside the requested bounds are lat 57.14-58.32 N and lon 22.80-23.98 E "
                "(60x60 cells, 0.02 deg grid); 3301 of 3600 cells were sea cells (finite SST on all 92 "
                "target days). One regional MHW event was detected, 2014-07-24 to 2014-08-18 (26 active days)."),
}
with open(os.path.join(OUT, "report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("written:", os.listdir(OUT))
'''
open('/work/write_out.py','w').write(script)
import runpy
runpy.run_path('/work/write_out.py', run_name='__main__')
