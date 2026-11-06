import numpy as np, xarray as xr, datetime, json, os

mask = np.load('/work/mask.npy')                 # (92, 3600)
lat_vals = np.load('/work/lat_vals.npy')         # float32 (60,)
lon_vals = np.load('/work/lon_vals.npy')         # float32 (60,)
sea = np.load('/work/sea_mask.npy')

os.makedirs('/work/output', exist_ok=True)

tgt_dates = []
d = datetime.date(2016,6,1)
while d <= datetime.date(2016,8,31):
    tgt_dates.append(d); d += datetime.timedelta(days=1)
time_vals = np.array([d.strftime('%Y-%m-%d') for d in tgt_dates], dtype='datetime64[ns]')

mask3d = mask.reshape(len(tgt_dates), len(lat_vals), len(lon_vals)).astype('uint8')
# land cells must be 0
flat = np.arange(3600).reshape(60, 60)
mask3d[:, ~sea.reshape(60,60)] = 0

ds = xr.Dataset(
    {'mhw': xr.DataArray(mask3d, dims=('time','lat','lon'),
                          attrs={'long_name':'marine heatwave mask (1 = inside per-cell MHW, 0 otherwise)'} )},
    coords={'time': ('time', time_vals),
            'latitude': ('lat', lat_vals),
            'longitude': ('lon', lon_vals)}
)
# rename latitude/longitude to lat/lon coordinate names? Spec: dims (time, lat, lon) with dataset coordinate values.
ds = ds.rename({'latitude':'lat','longitude':'lon'})
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print("wrote mhw_mask.nc")

report = {
    "region": {"lat_min": 64.51, "lat_max": 65.71, "lon_min": 21.97, "lon_max": 23.17},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2016-06-01", "end": "2016-08-31"},
    "events": [
        {"onset": "2016-06-01", "end": "2016-06-07"},
        {"onset": "2016-07-21", "end": "2016-08-13"}
    ],
    "complete": True,
    "caveats": ("Region grid is 60x60 cells (lat 64.52-65.70, lon 21.98-23.16); 314 of 3600 cells are land or have "
                "non-finite SST on at least one target day and are set to 0 in mhw. Baseline windows used "
                "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 beyond the 1992-2002 baseline. "
                "The first regional event starts on the first day of the target period, as analysis is "
                "restricted to 2016-06-01..2016-08-31 by design.")
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("wrote report.json")

# ---- read back and verify ----
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "dims:", chk['mhw'].dims)
print("unique:", np.unique(chk['mhw'].values))
print("time range:", chk['time'].values[0], chk['time'].values[-1])
print("lat range:", float(chk['lat'].values.min()), float(chk['lat'].values.max()))
print("lon range:", float(chk['lon'].values.min()), float(chk['lon'].values.max()))
print("per-cell MHW cell-days:", int(chk['mhw'].values.sum()))
with open('/work/output/report.json') as f:
    print(f.read())
