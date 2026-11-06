script = r'''
import numpy as np, xarray as xr, json, datetime as dt, os

CACHE='/work/cache'
raw_t=np.load(f'{CACHE}/raw_target.npy')
per_cell=np.load(f'{CACHE}/per_cell.npy')
events=json.load(open(f'{CACHE}/events.json'))

# dataset coordinate values
ds0=xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc', engine='h5netcdf')
lat=ds0.latitude.values[32:92].astype(np.float32)
lon=ds0.longitude.values[284:344].astype(np.float32)
ds0.close()
times=np.arange(np.datetime64('2008-06-01'), np.datetime64('2008-09-01'))
assert times.size==92==per_cell.shape[0] and lat.size==60 and lon.size==60

mhw=per_cell.astype(np.uint8)
assert mhw.shape==(92,60,60)
assert set(np.unique(mhw)).issubset({0,1})

ds=xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': times, 'lat': lat, 'lon': lon},
)
ds['mhw'].attrs={'long_name':'marine heatwave (per-cell) mask',
                 'flag_values':np.array([0,1],dtype=np.uint8),
                 'flag_meanings':'not_in_mhw in_mhw'}
ds['lat'].attrs={'units':'degrees_north','standard_name':'latitude'}
ds['lon'].attrs={'units':'degrees_east','standard_name':'longitude'}
ds['time'].attrs={'standard_name':'time'}
ds.attrs={'title':'Per-cell marine heatwave mask, Baltic Sea region, 2008-06-01..2008-08-31',
          'dataset_id':'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
          'baseline':'1992-2002 (pools include 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 edge days)',
          'region':'lat 54.13..55.33 N, lon 14.67..15.87 E (bounds inclusive)'}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

report={
 "region": {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87},
 "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
 "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
 "events": [{"onset": a, "end": b} for a,b in events],
 "complete": True,
 "caveats": ("Region bounds contain no grid-cell centres exactly at the limits; the analysed grid cells have "
             "lat 54.14..55.32 N and lon 14.68..15.86 E (all cells within the inclusive bounds, 60x60). "
             "Sea cells (3301 of 3600) are cells with finite SST on every target day. Baseline pools use the "
             "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 edge days required by the +-5-day windows "
             "around baseline dates; day-of-year 60 (29 February) has no pool of its own and was filled with "
             "the mean of days 59 and 61 before smoothing. Land cells are 0 in the mask."
            ),
}
json.dump(report, open('output/report.json','w'), indent=2)
print('written:')
for f in ['output/mhw_mask.nc','output/report.json']:
    print(' ', f, os.path.getsize(f), 'bytes')
print(json.dumps(report, indent=2)[:1200])
'''
open('/work/write_out.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/write_out.py'],capture_output=True,text=True)
print(r.stdout[-2500:]); print(r.stderr[-1500:])
