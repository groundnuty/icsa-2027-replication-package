import numpy as np, xarray as xr, json, os
from datetime import date

cwd = os.getcwd()
print("cwd:", cwd)
os.makedirs('output', exist_ok=True)

mask = np.load('/work/data/mask.npy')      # (92, nsea)
si = np.load('/work/data/sea_idx.npy')
tt = np.load('/work/data/tt.npy')
lat = np.load('/work/data/lat_sel.npy')    # float32, 60
lon = np.load('/work/data/lon_sel.npy')    # float32, 60
nsea = len(si)

# build full-region mask (60x60), land/other cells = 0
mfull = np.zeros((92, 60, 60), dtype=np.uint8)
mfull[:, si//60, si%60] = mask

ds = xr.Dataset()
ds['time'] = ('time', tt)
ds['lat'] = ('lat', lat)
ds['lon'] = ('lon', lon)
ds['mhw'] = ('time', 'lat', 'lon'), mfull
ds['time'].attrs = {'long_name': 'Time', 'standard_name': 'time', 'axis': 'T'}
ds['lat'].attrs = {'long_name': 'latitude', 'units': 'degrees_north', 'standard_name': 'latitude', 'axis': 'Y'}
ds['lon'].attrs = {'long_name': 'longitude', 'units': 'degrees_east', 'standard_name': 'longitude', 'axis': 'X'}
ds['mhw'].attrs = {'long_name': 'Marine heatwave mask', 'flag_values': [0, 1],
                   'flag_meanings': 'not_in_mhw in_mhw'}
ds.attrs = {
    'title': 'Baltic MHW mask, region 56.13-57.33N 17.71-18.91E, 2015-06-01..2015-08-31',
    'source': 'Copernicus Marine cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (reprocessed L4 daily)',
    'comment': ('mhw=1 where the cell is inside a per-cell MHW (>=5 consecutive days with SST >= smoothed 90th-percentile '
                'threshold from 1992-2002 baseline, 1-2 day gaps joined), 0 otherwise (land cells 0)'),
}
ds = ds.set_index(time=ds.time) if 'time' in ds else ds
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("wrote output/mhw_mask.nc")

# report
events = [{"onset": "2015-07-02", "end": "2015-07-07"}]
report = {
    "region": {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2015-06-01", "end": "2015-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Data read from the consolidated file icsa2027_data_20261101T090944Z/s2z/sst_s2.nc "
                "(1982-01-01..2023-12-31, verified identical to the daily s1z files for overlapping dates); "
                "the 1000 daily files in s1z cover only 1982-01-01..1984-09-26 and were not needed. "
                "Region grid cells: 60x60 (lat 56.14..57.32, lon 17.72..18.90, 0.02 deg grid); 3300 sea cells "
                "(finite SST on all 92 target days), 300 land cells (NaN) set to 0. All sea cells were complete "
                "over the 1992-2002 baseline, so every threshold/climatology pool had 121 valid values. "
                "Method: 90th percentile per day-of-year (MATLAB-default hazen/Type-5 quantile), day 60 set to the "
                "mean of days 59 and 61, then circular centred 31-day mean; hot = SST(K) >= threshold; per-cell MHW = "
                ">=5 consecutive hot days, runs separated by <=2 non-hot days joined (gap days included). "
                "All computations in float64."),
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")