import numpy as np, json, xarray as xr, os

mask = np.load('/work/mhw_mask.npy')
meta = json.load(open('/work/meta.json'))
tsecs = np.array(meta['time_secs_target'], dtype=np.int32)
lat = np.array(meta['lat_vals'], dtype=np.float32)
lon = np.array(meta['lon_vals'], dtype=np.float32)
mhw = mask.astype(np.uint8)

ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw,
             {"long_name": "per-cell marine heatwave mask (1 = cell inside a per-cell MHW, 0 otherwise; land = 0)",
              "flag_values": np.array([0,1], dtype=np.uint8),
              "flag_meanings": "not_in_mhw in_mhw"})},
    coords={
        "time": ("time", tsecs, {"units": "seconds since 1981-01-01", "calendar": "proleptic_gregorian",
                                  "standard_name": "time", "axis": "T"}),
        "lat": ("lat", lat, {"units": "degrees_north", "standard_name": "latitude", "axis": "Y"}),
        "lon": ("lon", lon, {"units": "degrees_east", "standard_name": "longitude", "axis": "X"}),
    },
    attrs={"title": "Marine heatwave mask, Baltic Sea region, 2005-06-01 to 2005-08-31",
           "source_dataset": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m",
           "region": "lat 59.05-60.25 N, lon 21.25-22.45 E (inclusive)"})
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print("rewritten")

# verify with default decoding
ds2 = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds2['mhw'].dtype, ds2['mhw'].shape)
m = ds2['mhw'].values
print("unique values:", np.unique(m), "sum:", int(m.sum()))
T = np.load('/work/T.npy'); sea = np.isfinite(T).all(axis=0)
print("mhw on land (must be 0):", int(m[:, ~sea].sum()))
print("matches computed mask:", np.array_equal(m, mask.astype(np.uint8)))
# events re-derivation
active = m.any(axis=(1,2))
idx = np.flatnonzero(active)
br = np.flatnonzero(np.diff(idx) > 1)
starts = np.concatenate(([idx[0]], idx[br+1])); ends = np.concatenate((idx[br], [idx[-1]]))
tdates = [date(2005,6,1)+timedelta(days=i) for i in range(m.shape[0])]
ev = [(tdates[s].isoformat(), tdates[e].isoformat()) for s,e in zip(starts,ends)]
rep = json.load(open('/work/output/report.json'))
print("events:", ev)
print("report match:", ev == [(e['onset'], e['end']) for e in rep['events']])
# raw on-disk dtype check
import h5py
with h5py.File('/work/output/mhw_mask.nc','r') as f:
    print("on-disk mhw dtype:", f['mhw'].dtype, "fill attr present:", '_FillValue' in f['mhw'].attrs)
print("output files:", os.listdir('/work/output'))
