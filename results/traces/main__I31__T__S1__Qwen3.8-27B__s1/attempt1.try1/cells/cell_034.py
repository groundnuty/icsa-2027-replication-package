
import numpy as np, xarray as xr, json, os, datetime

os.makedirs('output', exist_ok=True)
mask = np.load('work/mask_final.npy')           # (92, 3600) uint8, all zeros
lat = np.load('work/lat.npy')                   # float32 (60,)
lon = np.load('work/lon.npy')                   # float32 (60,)
m = mask.reshape(92, 60, 60)
t0 = datetime.date(2017,6,1)
times = np.array([(t0 + datetime.timedelta(days=i)) for i in range(92)], dtype='datetime64[ns]')

ds = xr.Dataset(
    data_vars={'mhw': xr.DataArray(m.astype(np.uint8), dims=('time','lat','lon'),
                                   attrs={'description': '1 = inside per-cell MHW, 0 = not (land cells are 0)'})},
    coords={'time': times, 'lat': lat, 'lon': lon},
)
ds.mhw.encoding = {'dtype': 'uint8'}
ds.lat.encoding = {'dtype': 'float32'}
ds.lon.encoding = {'dtype': 'float32'}
ds.to_netcdf('output/mhw_mask.nc')
print("written output/mhw_mask.nc")

report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2017-06-01", "end": "2017-08-31"},
    "events": [],
    "complete": True,
    "caveats": ("307 of 3600 region grid cells are land (non-finite SST) and set to 0. "
                "3293 sea cells were analysed. No per-cell MHW (>=5 consecutive hot days) occurred; "
                "longest per-cell hot streak was 3 days. SST exceeded the smoothed 90th-percentile threshold on only 6 days: "
                "2017-06-15 (1 cell), 2017-06-17 (113), 2017-06-18 (117), 2017-06-19 (102), 2017-06-20 (4) and 2017-07-10 (1), "
                "so no regional MHW events were detected for 2017-06-01 to 2017-08-31.")
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("written output/report.json")

# ---- read-back verification
chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
print("mhw dtype:", chk.mhw.dtype, "sum:", int(chk.mhw.values.sum()))
print("time:", str(chk.time.values[0]), "->", str(chk.time.values[-1]), "n=", chk.sizes['time'])
print("lat:", float(chk.lat.values[0]), "->", float(chk.lat.values[-1]), "n=", chk.sizes['lat'])
print("lon:", float(chk.lon.values[0]), "->", float(chk.lon.values[-1]), "n=", chk.sizes['lon'])
chk.close()
print(open('output/report.json').read())
