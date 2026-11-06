import numpy as np, xarray as xr, json, os
import fsspec, h5py

fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        lat = h['latitude'][350:410].astype(np.float32)
        lon = h['longitude'][413:473].astype(np.float32)

mask = np.load('/tmp/mhw/mask.npy')   # (92,60,60) uint8
time = np.array([np.datetime64('2010-06-01') + np.timedelta64(k,'D') for k in range(92)], dtype='datetime64[ns]')

ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mask)},
    coords={'time': time, 'lat': lat, 'lon': lon},
)
ds['mhw'].attrs = {
    'long_name': 'marine heatwave (per-cell MHW) mask',
    'flag_values': np.array([0,1], dtype=np.uint8),
    'flag_meanings': 'not_in_mhw in_mhw',
    'units': '1',
}
ds['lat'].attrs = {'standard_name':'latitude','units':'degrees_north','axis':'Y'}
ds['lon'].attrs = {'standard_name':'longitude','units':'degrees_east','axis':'X'}
ds.attrs['title'] = 'Marine heatwave mask, Baltic Sea region 60.49-61.69N 17.25-18.45E, 2010-06-01 to 2010-08-31'
ds.attrs['source'] = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, DMI)'
ds.attrs['method'] = ('baseline 1992-2002 (+/-5-day windows incl. 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05); '
                      '90th percentile (Hazen/type-5) thresholds and mean climatology per day of year, day-60 patched to '
                      'mean of days 59 and 61, smoothed with wrapped centred 31-day moving mean; hot days SST>=threshold '
                      '(kelvin); per-cell MHW >=5 hot days, 1-2-day gaps joined; regional day active if any sea cell in MHW')

os.makedirs('output', exist_ok=True)
enc = {
    'mhw': {'dtype':'uint8','_FillValue':None,'zlib':True,'complevel':4},
    'time': {'units':'seconds since 1981-01-01','calendar':'proleptic_gregorian','dtype':'int64'},
    'lat': {'_FillValue':None}, 'lon': {'_FillValue':None},
}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print('wrote output/mhw_mask.nc')

ev = json.load(open('/tmp/mhw/events.json'))
caveat = ("Sea cells = region cells with finite SST on every target day (3293 of 3600 grid cells; the 307 excluded "
          "cells are NaN on all 92 target days, consistent with land). Thresholds and climatology use the 1992-2002 "
          "baseline with the method's +/-5-calendar-day windows, which reach 1991-12-27..1991-12-31 and "
          "2003-01-01..2003-01-05; hence baseline_analysed spans those extension days. Computation in float64; SST "
          "compared in kelvin as stored. The single regional event ends on 2010-07-23, the last day before the first "
          "day on which no sea cell is inside a per-cell MHW.")
report = {
    'region': {'lat_min': 60.49, 'lat_max': 61.69, 'lon_min': 17.25, 'lon_max': 18.45},
    'baseline_analysed': {'start': '1991-12-27', 'end': '2003-01-05'},
    'target_analysed': {'start': '2010-06-01', 'end': '2010-08-31'},
    'events': [{'onset': e[0], 'end': e[1]} for e in ev],
    'complete': True,
    'caveats': caveat,
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('wrote output/report.json')
