import os, json
import numpy as np, xarray as xr

z = np.load('/work/region.npz'); m = np.load('/work/mhw.npz')
mhw = m['mhw'].reshape(92, 60, 60).astype(np.uint8)
lat = z['lat'].astype('float32')   # dataset values
lon = z['lon'].astype('float32')
times = np.array([x.decode() if isinstance(x, bytes) else str(x) for x in z['tgt_dates']], dtype='datetime64[ns]')

os.makedirs('output', exist_ok=True)
ds = xr.Dataset(
    {'mhw': (('time', 'latitude', 'longitude'), mhw, {'long_name': 'per-cell MHW membership (1=inside per-cell MHW, 0=otherwise; land=0)'})},
    coords={'time': ('time', times, {'standard_name': 'time', 'units': 'days since 1858-11-17T00:00:00Z'}),
            'latitude': ('latitude', lat, {'units': 'degrees_north', 'standard_name': 'latitude'}),
            'longitude': ('longitude', lon, {'units': 'degrees_east', 'standard_name': 'longitude'})})
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

report = {
    "region": {"lat_min": 57.33, "lat_max": 58.53, "lon_min": 9.03, "lon_max": 10.23},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": "2021-07-03", "end": "2021-07-29"}],
    "complete": True,
    "caveats": "Thresholds/climatology computed from the 1992-2002 baseline with +/-5-day day-of-year windows (extending 1991-12-27 to 2003-01-05), 90th percentile via Hazen/linear interpolation in float64, day-60 filled from days 59/61, then 31-day centred wrap-around smoothing; MHWs: >=5 consecutive days with SST >= threshold, gaps of <=2 non-hot days joined. One regional event detected 2021-07-03 to 2021-07-29."
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

# verify
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk.mhw.dtype, "sum:", int(chk.mhw.sum()))
print("lat[0],lat[-1]:", chk.latitude.values[0], chk.latitude.values[-1])
print("lon[0],lon[-1]:", chk.longitude.values[0], chk.longitude.values[-1])
print("time[0],time[-1]:", chk.time.values[0], chk.time.values[-1])
chk.close()
print(open('output/report.json').read())
