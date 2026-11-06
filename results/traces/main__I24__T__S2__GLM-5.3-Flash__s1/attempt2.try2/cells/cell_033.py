import numpy as np, pickle, json, os
import xarray as xr

mhw = np.load("/work/mhw.npy")          # (92,60,60) uint8
sea = np.load("/work/sea.npy")
with open("/work/dates_ext_tgt.pkl","rb") as fh: dd = pickle.load(fh)
tgt_dates = dd["tgt_dates"]             # datetime64[D] array, 92 entries
with open("/work/events.pkl","rb") as fh: ev = pickle.load(fh)

# dataset coordinate values for the region (float32, as in source)
lat_all = np.array([57.52 + 0.02*k for k in range(1)], dtype=np.float32)  # placeholder
# read actual coordinate arrays from the dataset
import fsspec, h5py
fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
with h5py.File(f, "r") as h5:
    lat_ds = h5["latitude"][:]   # float32
    lon_ds = h5["longitude"][:]
la = lat_ds.astype('float64'); lo = lon_ds.astype('float64')
lat_idx = np.where((la >= 57.57) & (la <= 58.77))[0]
lon_idx = np.where((lo >= 10.25) & (lo <= 11.45))[0]
lat_region = lat_ds[lat_idx[0]:lat_idx[-1]+1]   # float32 dataset values
lon_region = lon_ds[lon_idx[0]:lon_idx[-1]+1]
print("lat_region:", lat_region.dtype, lat_region[0], "...", lat_region[-1], lat_region.size)
print("lon_region:", lon_region.dtype, lon_region[0], "...", lon_region[-1], lon_region.size)

time_vals = tgt_dates.astype("datetime64[ns]")
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw)},
    coords={"time": time_vals, "lat": lat_region, "lon": lon_region},
)
ds_out["mhw"].attrs = {"long_name": "marine heatwave (per-cell) mask on target days",
                       "flag_values": np.array([0, 1], dtype=np.uint8),
                       "flag_meanings": "not_in_mhw in_mhw"}
ds_out["lat"].attrs = {"units": "degrees_north", "standard_name": "latitude"}
ds_out["lon"].attrs = {"units": "degrees_east", "standard_name": "longitude"}
ds_out["time"].attrs = {"standard_name": "time", "axis": "T"}
ds_out.attrs = {"title": "Per-cell marine heatwave mask, Baltic Sea region, 2004-06-01 to 2004-08-31",
                "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
                "region": "lat 57.57-58.77 N (inclusive), lon 10.25-11.45 E (inclusive)"}
enc = {"mhw": {"dtype": "uint8", "_FillValue": None},
       "time": {"units": "seconds since 1981-01-01", "dtype": "int32", "calendar": "proleptic_gregorian"},
       "lat": {"dtype": "float32"}, "lon": {"dtype": "float32"}}

os.makedirs("/work/output", exist_ok=True)
ds_out.to_netcdf("/work/output/mhw_mask.nc", engine="h5netcdf", encoding=enc)
print("wrote /work/output/mhw_mask.nc")

# --- report.json ---
reg_ev = ev["regional"]
events = [{"onset": str(np.datetime64(tgt_dates[s], "D"))[:10],
           "end": str(np.datetime64(tgt_dates[e], "D"))[:10]} for s, e in reg_ev]
report = {
    "region": {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Grid step is 0.02 deg, so the inclusive bounds select cell centres "
                "57.58-58.76 N and 10.26-11.44 E (60x60 cells; 3304 sea cells with SST finite on all "
                "92 target days, 296 land cells masked 0). Baseline pools use the extended window "
                "1991-12-27 to 2003-01-05 as specified (all 4028 days used; every day-of-year pool "
                "holds 121 values per cell). Analysis restricted to the target period as specified."
                ),
}
with open("/work/output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote /work/output/report.json")
print(json.dumps(report, indent=2))
