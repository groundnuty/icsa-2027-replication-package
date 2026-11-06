import os, json
import numpy as np, xarray as xr
from datetime import date, timedelta

os.makedirs('/work/output', exist_ok=True)

# dataset coordinate values (float32, as stored)
ds0 = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
LAT = ds0['latitude'].values  # float32
LON = ds0['longitude'].values
latm = (LAT >= 61.57) & (LAT <= 62.77)
lonm = (LON >= 20.17) & (LON <= 21.37)
lat_c = LAT[latm]
lon_c = LON[lonm]

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f) if False else None
import pickle
with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
tgt_dates = dd['tgt']
time_c = np.array([d.isoformat() + 'T00:00:00' for d in tgt_dates], dtype='datetime64[ns]')

mhw = np.load('/work/mhw.npy')  # (92, 3600)
mhw3 = mhw.reshape(len(tgt_dates), 60, 60)
print("mhw3 shape:", mhw3.shape, mhw3.dtype, "sum:", int(mhw3.sum()))

da = xr.DataArray(mhw3, dims=('time','lat','lon'),
                  coords={'time': ('time', time_c), 'lat': ('lat', lat_c), 'lon': ('lon', lon_c)},
                  name='mhw',
                  attrs={'description': 'Per-cell MHW mask, 1 = inside per-cell MHW (incl. merged gap days), 0 otherwise (land=0). Region lat 61.57-62.77N, lon 20.17-21.37E.'})
ds = da.to_dataset()
ds.to_netcdf('/work/output/mhw_mask.nc')
print("wrote /work/output/mhw_mask.nc")

ev = pickle.load(open('/work/events.pkl','rb'))
report = {
    "region": {"lat_min": 61.57, "lat_max": 62.77, "lon_min": 20.17, "lon_max": 21.37},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in ev],
    "complete": True,
    "caveats": ("Region grid: 60x60 cells (lat 61.58-62.76, lon 20.18-21.36 at 0.02 deg); 3308 sea cells (finite SST on all "
                "92 target days), 292 land cells set to 0. Baseline 1992-2002; threshold/climatology pools for each day of "
                "year d (leap-year day-of-year mapping, 29 Feb = 60, day 60 has no pool) use all SST values within +/-5 "
                "calendar days of baseline dates of day d, extending to 1991-12-27 and 2003-01-05; 29 Feb values fall into "
                "the windows of their calendar neighbours. Day 60 set to the mean of days 59 and 61 before a 31-day centred "
                "wrap-around moving mean. Thresholds are the 90th percentile of each pool via numpy method='hazen' (Hyndman-Fan "
                "type 5, NaN ignored); all computations in float64; SST compared in kelvin with '>='. Per-cell MHWs are runs of "
                ">=5 consecutive hot days joined across 1-2 day gaps (gap days included). No target day was missing data.")
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print("wrote /work/output/report.json")
print(json.dumps(report, indent=2)[:1500])
