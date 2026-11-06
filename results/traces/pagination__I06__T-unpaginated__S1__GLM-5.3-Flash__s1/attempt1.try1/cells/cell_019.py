import numpy as np, datetime as dt, json, os, pickle
import xarray as xr

mhw_mask = np.load('/tmp/mhw_mask.npy')          # (92, 60, 60) uint8
with open('/tmp/meta.pkl','rb') as f: meta = pickle.load(f)
targ_dates = [dt.date.fromisoformat(s) for s in meta['targ_dates']]
with open('/tmp/events.pkl','rb') as f: events = pickle.load(f)

# grid coords from the dataset
import fsspec, h5py
fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20120601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        lat = h['latitude'][:].astype(np.float32)     # full grid
        lon = h['longitude'][:].astype(np.float32)
        tsec = int(h['time'][0])
        t_units = h['time'].attrs['units'].decode()
        t_cal = h['time'].attrs['calendar'].decode()
lat_reg = lat[48:108]; lon_reg = lon[353:413]
print("lat_reg[0],[-1]:", lat_reg[0], lat_reg[-1], " lon_reg[0],[-1]:", lon_reg[0], lon_reg[-1])

time64 = np.array([np.datetime64(d, 'ns') for d in targ_dates])
ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw_mask)},
    coords={
        "time": ("time", time64),
        "lat": ("lat", lat_reg),
        "lon": ("lon", lon_reg),
    },
)
ds["mhw"].attrs = {"long_name": "marine heatwave mask (per-cell MHW)", "flag_values": np.array([0,1], dtype=np.uint8),
                   "flag_meanings": "not_in_mhw in_mhw"}
ds["lat"].attrs = {"units": "degrees_north", "standard_name": "latitude"}
ds["lon"].attrs = {"units": "degrees_east", "standard_name": "longitude"}
enc = {
    "mhw": {"dtype": "uint8", "_FillValue": None, "zlib": True},
    "time": {"units": t_units, "calendar": t_cal, "dtype": "int32"},
    "lat": {"_FillValue": None, "zlib": True},
    "lon": {"_FillValue": None, "zlib": True},
}
os.makedirs('output', exist_ok=True)
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [{"onset": s, "end": e} for s,e in events],
    "complete": True,
    "caveats": "",
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))

# ---- verify written files ----
back = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(back)
print("mhw dtype:", back['mhw'].dtype, "dims:", back['mhw'].dims, "shape:", back['mhw'].shape)
m = back['mhw'].values
print("values unique:", np.unique(m), " sum:", m.sum(), " equal to computed:", np.array_equal(m, mhw_mask))
print("time values:", back['time'].values[0], "->", back['time'].values[-1])
print("lat/lon match region:", np.array_equal(back['lat'].values, lat_reg), np.array_equal(back['lon'].values, lon_reg))
back.close()
with open('output/report.json') as f:
    r = json.load(f)
print("report keys:", sorted(r.keys()))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print("files in output:", os.listdir('output'))
