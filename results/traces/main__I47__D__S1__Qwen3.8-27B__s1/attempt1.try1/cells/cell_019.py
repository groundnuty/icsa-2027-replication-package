import os, json
import numpy as np
import xarray as xr

m = np.load('/work/mask.npz')
mask = m['mask']; tgt_dates = [d for d in m['tgt_dates']]
data = np.load('/work/S.npz', allow_pickle=True)
S_tgt = data['S_tgt']
reg_lat = data['reg_lat']; reg_lon = data['reg_lon']
sea = np.isfinite(S_tgt).all(axis=0)

nlat, nlon = 60, 60
R = np.zeros((92, nlat, nlon), dtype=np.uint8)
sea_cells = np.flatnonzero(sea)
sea_idx = np.unravel_index(sea_cells, (nlat, nlon))
R[:, sea_idx[0], sea_idx[1]] = mask
assert R.sum() == mask.sum()

time_coord = np.array([f"{d}T00:00:00" for d in tgt_dates], dtype='datetime64[ns]')
ds = xr.Dataset(
    {'mhw': xr.DataArray(R, dims=('time','lat','lon'),
                         coords={'time': time_coord, 'lat': ('lat', reg_lat.astype(np.float32)),
                                 'lon': ('lon', reg_lon.astype(np.float32))},
                         encoding={'dtype': 'uint8', '_FillValue': None, 'zlib': True},
                         attrs={'description': 'Per-cell MHW mask: 1 if cell inside a per-cell MHW on that day, 0 otherwise (land cells 0). Region lat 64.39-65.59N, lon 23.41-24.61E, 2019-06-01..2019-08-31.'})}
)
os.makedirs('/work/output', exist_ok=True)
os.makedirs('output', exist_ok=True)
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

report = {
  "region": {"lat_min": 64.39, "lat_max": 65.59, "lon_min": 23.41, "lon_max": 24.61},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
  "events": [
    {"onset": "2019-06-06", "end": "2019-06-22"},
    {"onset": "2019-07-20", "end": "2019-07-29"}
  ],
  "complete": True,
  "caveats": ("Sea cells (3311 of 3600 region cells) had finite SST on all 92 target days; the 289 non-sea cells "
              "(persistent land/no-data) are set to 0. Baseline 1992-2002 pools used +/-5-day windows, including "
              "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; all pool values were finite so no NaN-ignoring was "
              "actually triggered. Two regional MHW events were detected in 2019.")
}
with open('/work/output/report.json','w') as f: json.dump(report, f, indent=2)
with open('output/report.json','w') as f: json.dump(report, f, indent=2)
print("written")

# verify output
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "sum:", int(chk['mhw'].values.sum()))
print("time first/last:", chk['time'].values[0], chk['time'].values[-1])
print(json.load(open('output/report.json')))
