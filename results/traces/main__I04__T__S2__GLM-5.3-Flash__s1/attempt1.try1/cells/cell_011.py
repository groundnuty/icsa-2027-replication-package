import numpy as np, os, json, xarray as xr

cwd = os.getcwd()
print('cwd:', cwd)
outdir = os.path.join(cwd, 'output')
os.makedirs(outdir, exist_ok=True)
print('outdir:', outdir, os.listdir(outdir) if os.path.exists(outdir) else 'new')

dates = np.load('/tmp/dates.npy')
tgt_dates = dates[14031:14123]                      # datetime64[D]
mhw_full = np.load('/tmp/mhw_full.npy')             # (92,60,60) uint8

# dataset coordinate values for the region (float32 as stored)
lat_reg = np.arange(45, 105) * 0.02 + 53.5
lon_reg = np.arange(463, 523) * 0.02 + 9.0
# recompute exactly from known grid: lat = 53.5 + 0.02*i, lon = 9.0 + 0.02*j
lat_reg = (53.5 + 0.02*np.arange(45, 105)).astype(np.float32)
lon_reg = (9.0  + 0.02*np.arange(463, 523)).astype(np.float32)
print('lat[0],[−1]:', lat_reg[0], lat_reg[-1], '| lon[0],[−1]:', lon_reg[0], lon_reg[-1])

time64 = tgt_dates.astype('datetime64[ns]')
ds = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw_full)},
    coords={'time': time64, 'lat': lat_reg, 'lon': lon_reg},
)
ds['mhw'].encoding = {'_FillValue': None, 'dtype': 'uint8'}
enc = {'mhw': {'zlib': True, 'complevel': 4, '_FillValue': None, 'dtype': 'uint8'},
       'time': {'units': 'seconds since 1981-01-01', 'calendar': 'proleptic_gregorian'},
       'lat': {'dtype': 'float32'}, 'lon': {'dtype': 'float32'}}
ncpath = os.path.join(outdir, 'mhw_mask.nc')
ds.to_netcdf(ncpath, engine='h5netcdf', encoding=enc)
print('wrote', ncpath, os.path.getsize(ncpath)/1e6, 'MB')

# verify
chk = xr.open_dataset(ncpath, engine='h5netcdf')
print(chk)
print('mhw dtype:', chk.mhw.dtype, 'dims:', chk.mhw.dims, 'sum:', int(chk.mhw.values.sum()))
print('time0/last:', chk.time.values[0], chk.time.values[-1], 'n=', chk.sizes['time'])
chk.close()

ev = json.load(open('/tmp/events.json'))['events']
td = [str(d) for d in tgt_dates]
report = {
    'region': {'lat_min': 54.39, 'lat_max': 55.59, 'lon_min': 18.25, 'lon_max': 19.45},
    'baseline_analysed': {'start': '1992-01-01', 'end': '2002-12-31'},
    'target_analysed': {'start': td[0], 'end': td[-1]},
    'events': [{'onset': td[s], 'end': td[e]} for s, e in ev],
    'complete': True,
    'caveats': ('Sea cells: the 3309 region cells with finite SST on every target day (constant land mask, '
                '291 land cells). All 92 target days and the full 1992-2002 baseline (incl. +/-5-day extension '
                'data) were analysed with no missing sea-cell data; threshold/climatology DOYs 153-244 were used.'),
}
with open(os.path.join(outdir, 'report.json'), 'w') as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))
