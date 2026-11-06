import numpy as np, xarray as xr, datetime, json

mask = np.load('/work/mask.npy')
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')
sea = np.load('/work/sea_mask.npy')

tgt_dates = []
d = datetime.date(2016,6,1)
while d <= datetime.date(2016,8,31):
    tgt_dates.append(d); d += datetime.timedelta(days=1)
time_vals = np.array([d.strftime('%Y-%m-%d') for d in tgt_dates], dtype='datetime64[ns]')
mask3d = mask.reshape(len(tgt_dates), 60, 60).astype('uint8')
mask3d[:, ~sea.reshape(60,60)] = 0

ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mask3d,
             {'long_name': 'marine heatwave mask (1 = inside per-cell MHW, 0 otherwise; land cells 0)'})},
    coords={'time': ('time', time_vals),
            'lat': ('lat', lat_vals),
            'lon': ('lon', lon_vals)}
)
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')

chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(chk)
assert chk['mhw'].dtype == np.uint8
assert chk.dims == {'time': 92, 'lat': 60, 'lon': 60}
assert list(chk['lat'].values[:2]) == [lat_vals[0], lat_vals[1]]
assert np.array_equal(chk['lat'].values, lat_vals) and np.array_equal(chk['lon'].values, lon_vals)
assert chk['time'].values[0] == np.datetime64('2016-06-01') and chk['time'].values[-1] == np.datetime64('2016-08-31')
print("NetCDF verified OK")

# boundary sanity around events (active day counts per target day)
active = mask3d.any(axis=(1,2))
for i in [0,1,2,3,4,5,6,7,8, 50,51,52, 69,70,71,72,73]:
    print(tgt_dates[i].strftime('%Y-%m-%d'), "active" if active[i] else "-", "cells:", int(mask3d[i].sum()))

# also confirm the two events in report match mask
ev = []
i = 0
nt = 92
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        ev.append((str(tgt_dates[i]), str(tgt_dates[j]))); i = j+1
    else: i += 1
rep = json.load(open('/work/output/report.json'))
print("events from mask:", ev)
print("events in report:", [(e['onset'], e['end']) for e in rep['events']])
assert ev == [(e['onset'], e['end']) for e in rep['events']]
print("ALL GOOD")
