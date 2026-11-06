import os, json
import numpy as np, xarray as xr

z = np.load('/work/region.npz'); m = np.load('/work/mhw.npz')
mhw = m['mhw'].reshape(92, 60, 60).astype(np.uint8)
lat = z['lat'].astype('float32')
lon = z['lon'].astype('float32')
times = np.array([str(x) for x in z['tgt_dates']], dtype='datetime64[ns]')

os.makedirs('output', exist_ok=True)
ds = xr.Dataset(
    {'mhw': (('time', 'latitude', 'longitude'), mhw,
             {'long_name': 'per-cell MHW membership (1=inside per-cell MHW incl. gap days, 0 otherwise; land cells 0)',
              'flag_values': [0, 1], 'flag_meanings': ['not in MHW', 'in MHW']})},
    coords={'time': ('time', times, {'standard_name': 'time'}),
            'latitude': ('latitude', lat, {'units': 'degrees_north', 'standard_name': 'latitude', 'long_name': 'latitude'}),
            'longitude': ('longitude', lon, {'units': 'degrees_east', 'standard_name': 'longitude', 'long_name': 'longitude'})},
    attrs={'title': 'Per-cell MHW mask, Baltic Sea region 57.33-58.53N 9.03-10.23E, 2021-06-01 to 2021-08-31',
           'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m', 'method': 'Baltic MHW catalogue method (1992-2002 baseline, 90th pct hazen, 31d wrap smoothing, >=5d runs, <=2d gap join)'})
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

report = {
    "region": {"lat_min": 57.33, "lat_max": 58.53, "lon_min": 9.03, "lon_max": 10.23},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": "2021-07-03", "end": "2021-07-29"}],
    "complete": True,
    "caveats": "Thresholds/climatology from 1992-2002 baseline, +/-5-calendar-day windows per day-of-year (data used 1991-12-27 to 2003-01-05), 90th percentile (Hazen) and mean in float64 ignoring NaN, day 60 set to mean of days 59 and 61, then 31-day centred wrap-around smoothing. A day is hot if SST >= threshold for that day of year; MHWs are >=5 consecutive hot days joined across <=2 non-hot-day gaps. One regional event detected: 2021-07-03 to 2021-07-29."
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk.mhw.dtype, "sum:", int(chk.mhw.sum()))
print("time[0], time[-1]:", chk.time.values[0], chk.time.values[-1], "n:", chk.sizes['time'])
print("lat range:", float(chk.latitude.values[0]), float(chk.latitude.values[-1]), "n:", chk.sizes['latitude'])
print("lon range:", float(chk.longitude.values[0]), float(chk.longitude.values[-1]), "n:", chk.sizes['longitude'])
print("unique mhw vals:", np.unique(chk.mhw.values))
chk.close()
print(json.dumps(json.load(open('output/report.json')), indent=1)[:1200])
