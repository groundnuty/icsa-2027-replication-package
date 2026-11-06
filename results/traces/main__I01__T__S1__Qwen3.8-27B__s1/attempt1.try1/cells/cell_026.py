import json, os
import numpy as np
import xarray as xr
from datetime import date, timedelta

meta = json.load(open('/tmp/meta.json'))
lat_region = np.array(meta['lat32'], dtype=np.float32)
lon_region = np.array(meta['lon32'], dtype=np.float32)
z = np.load('/tmp/mhw_final.npz')
in_mhw = z['in_mhw']; sea_idx = z['sea_idx']
tgt_dates = [date(2008,6,1) + timedelta(days=k) for k in range(92)]

mhw = np.zeros((92, 60, 60), dtype=np.uint8)
row, col = np.unravel_index(sea_idx, (60, 60))
for t in range(92):
    mhw[t, row, col] = in_mhw[:, t].astype(np.uint8)

time_coord = np.array([np.datetime64(str(d), 'ns') for d in tgt_dates])
ds_out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw)},
    coords={'time': time_coord, 'lat': lat_region, 'lon': lon_region},
)
ds_out.to_netcdf('/work/output/mhw_mask.nc')

chk = xr.open_dataset('/work/output/mhw_mask.nc')
print(chk)
print("dtype:", chk['mhw'].dtype, "dims:", dict(chk.sizes), "unique:", np.unique(chk['mhw'].values))
print("lat range:", float(chk['lat'].min()), float(chk['lat'].max()))
print("lon range:", float(chk['lon'].min()), float(chk['lon'].max()))
print("time range:", chk['time'].values[0], chk['time'].values[-1])
print("mask total ones:", int(chk['mhw'].sum()), "active days:", int((chk['mhw'].sum(axis=(1,2))>0).sum()))
chk.close()
print("report:", open('/work/output/report.json').read())
