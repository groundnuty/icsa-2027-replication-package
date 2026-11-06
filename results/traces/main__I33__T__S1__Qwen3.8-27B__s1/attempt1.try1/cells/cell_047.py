
import numpy as np, pickle
import xarray as xr

lat_r = np.load('/work/work/lat_r.npy')
lon_r = np.load('/work/work/lon_r.npy')
M_a = np.load('/work/work/M_a.npy')
S_t = np.load('/work/work/S_t.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']

mask = np.zeros((len(target_dates), 60, 60), dtype=np.uint8)
mask[:, sea[:,0], sea[:,1]] = M_a.astype(np.uint8)
print("mask sum:", int(mask.sum()), "(expect 80031)")

time_arr = np.array([np.datetime64(t.isoformat()) for t in target_dates], dtype='datetime64[ns]')
out = xr.Dataset(
    {'mhw': (('time','latitude','longitude'), mask)},
    coords={'time': time_arr, 'latitude': lat_r, 'longitude': lon_r}
)
out['mhw'].attrs = {'long_name': 'per-cell MHW membership (1) / not in MHW or land (0)'}
out.attrs = {
    'title': 'Baltic Sea MHW mask, region 59.05-60.25N 21.25-22.45E, 2014-06-01..2014-08-31',
    'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, version 202506)',
    'method': ('threshold = 90th percentile (hazen, Hyndman-Fan type 5 = MATLAB default) of the +/-5-calendar-day '
               'day-of-year pool from baseline 1992-2002, incl. 5-day extensions 1991-12-27..1991-12-31 and '
               '2003-01-01..2003-01-05; climatology = pool mean; day-of-year 60 set to mean of days 59 and 61; '
               'both smoothed with 31-day centred circular moving mean; all in float64; '
               'hot day: SST(kelvin) >= threshold; per-cell MHW: run >=5 consecutive hot days; '
               'MHWs separated by 1-2 non-hot days joined, gap days included'),
    'conventions': 'CF-1.4',
}
out.to_netcdf('/work/output/mhw_mask.nc')

ds2 = xr.open_dataset('/work/output/mhw_mask.nc')
v = ds2['mhw'].values
print("dtype:", v.dtype, "shape:", v.shape, "sum:", int(v.sum()), "unique:", np.unique(v))
print("time:", ds2['time'].values[0], "->", ds2['time'].values[-1], "n=", ds2['time'].size)
print("lat:", ds2['latitude'].values[0], "->", ds2['latitude'].values[-1], "n=", ds2['latitude'].size, ds2['latitude'].dtype)
print("lon:", ds2['longitude'].values[0], "->", ds2['longitude'].values[-1], "n=", ds2['longitude'].size, ds2['longitude'].dtype)

land = ~np.all(np.isfinite(S_t), axis=0)
print("land cells all zero:", bool((v.sum(axis=0)[land] == 0).all()))
sea_col_sum = v.sum(axis=0)[~land].ravel()
expected = M_a.sum(axis=0)
# map: sea cells in row-major over the 60x60 mask
sel = np.argwhere(~land)
print("sea cells match M_a:", bool(np.array_equal(v.sum(axis=0)[sel[:,0], sel[:,1]], M_a.sum(axis=0))))
