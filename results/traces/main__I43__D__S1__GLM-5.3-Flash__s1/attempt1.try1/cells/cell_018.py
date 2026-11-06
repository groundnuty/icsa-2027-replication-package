import os, json, datetime as dt
# verify all files are present locally
dates = json.load(open('/work/dates.json'))
need = [dt.date.fromisoformat(s) for s in dates['baseline_window'] + dates['target']]
have = set(f[4:12] for f in os.listdir('/work/nc') if f.endswith('.nc'))
missing = [str(d) for d in need if f'{d:%Y%m%d}' not in have]
print('missing:', missing)
# sanity check a couple of files open
import xarray as xr
for f in ['sst_19911227.nc','sst_20030105.nc','sst_20170831.nc']:
    ds = xr.open_dataset(f'/work/nc/{f}', engine='h5netcdf')
    print(f, ds['time'].values[0], ds['analysed_sst'].shape)
    ds.close()
