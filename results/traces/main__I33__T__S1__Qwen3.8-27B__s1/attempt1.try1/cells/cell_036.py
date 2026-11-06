
import numpy as np, pickle, os, fsspec, xarray as xr
import datetime
os.makedirs('/work/output', exist_ok=True)

fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20140601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values.copy()   # float32
    lon = ds['longitude'].values.copy()  # float32
    tenc = ds['analysed_sst'].encoding.get('_FillValue')
lat_r = lat[278:338]
lon_r = lon[613:673]
np.save('/work/work/lat_r.npy', lat_r)
np.save('/work/work/lon_r.npy', lon_r)
print("lat_r:", lat_r[:3], lat_r[-3:], lat_r.dtype, "lon_r:", lon_r[:3], lon_r[-3:], lon_r.dtype)
print("raw time variable:", ds['time'].values, ds['time'].dtype)

M = np.load('/work/work/M.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']

mask = np.zeros((len(target_dates), 60, 60), dtype=np.uint8)
mask[:, sea[:,0], sea[:,1]] = M.astype(np.uint8)
print("mask sum:", int(mask.sum()), " max:", mask.max())

time_arr = np.array([t.to_datetime64() for t in target_dates], dtype='datetime64[ns]')
out = xr.Dataset(
    {'mhw': (('time','latitude','longitude'), mask)},
    coords={'time': time_arr, 'latitude': lat_r, 'longitude': lon_r}
)
out['mhw'].attrs = {'long_name': 'per-cell MHW membership (1) / not in MHW or land (0)', 'dtype_note': 'uint8'}
out.attrs = {
    'title': 'Baltic Sea MHW mask, region 59.05-60.25N 21.25-22.45E, 2014-06-01..2014-08-31',
    'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, version 202506)',
    'method': 'threshold = 90th pct (hazen) of +/-5-day day-of-year pool, baseline 1992-2002 (+5-day edge extensions 1991-12-27..1991-12-31, 2003-01-01..2003-01-05); 31-day centred circular smoothing; MHW = run >=5 hot days (SST>=threshold), gaps of 1-2 days joined',
    'conventions': 'CF-1.4',
}
out.to_netcdf('/work/output/mhw_mask.nc')
print("wrote mhw_mask.nc")
# read back check
ds2 = xr.open_dataset('/work/output/mhw_mask.nc')
print(ds2)
print("dtype:", ds2['mhw'].dtype, "sum:", int(ds2['mhw'].values.sum()))
print("lat first/last:", ds2['latitude'].values[0], ds2['latitude'].values[-1])
print("lon first/last:", ds2['longitude'].values[0], ds2['longitude'].values[-1])
print("time first/last:", ds2['time'].values[0], ds2['time'].values[-1])
