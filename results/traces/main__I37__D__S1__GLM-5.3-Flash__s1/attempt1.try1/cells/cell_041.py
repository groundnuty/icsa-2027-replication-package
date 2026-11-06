import numpy as np, datetime as dt, json, os

sst = np.load('/work/sst_cube.npy')
sea = np.load('/work/sea_mask.npy')

# Final consistency check: union of pools covers all baseline dates
NB = 4027
CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
dates_all = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(NB)]
doys_all = np.array([sum(CUM[:d.month-1])+d.day for d in dates_all])
yrs = np.array([d.year for d in dates_all])
base_pos = np.where((yrs>=1992)&(yrs<=2002))[0]
base_doys = doys_all[base_pos]
used = np.zeros(len(base_pos), dtype=bool)
for d in range(1, 367):
    if d == 60: continue
    w = (((d-1+np.arange(-5,6))%366)+1)
    used |= np.isin(base_doys, w)
print("baseline days used by pools:", int(used.sum()), "of", len(base_pos))
first_used = min(d for d,p in zip(dates_all, np.arange(NB)) if p in set(base_pos[used]))
last_used  = max(d for d,p in zip(dates_all, np.arange(NB)) if p in set(base_pos[used]))
bp_used = set(base_pos[used].tolist())
first_used = min(dt.date(1991,12,27)+dt.timedelta(days=int(p)) for p in bp_used)
last_used  = max(dt.date(1991,12,27)+dt.timedelta(days=int(p)) for p in bp_used)
print("first/last baseline day actually used:", first_used, last_used)

# Build final mask: (92, 61, 61) uint8, zeros
runs = np.load('/work/mhw_runs.npy')          # (92, C) bool, all False
sea_flat_idx = np.where(sea.ravel())[0]
mask = np.zeros((92, 61, 61), dtype=np.uint8)
runs_full = np.zeros((92, 61, 61), dtype=bool)
runs_full.reshape(92, -1)[:, sea_flat_idx] = runs
mask[runs_full] = 1
print("mask sum:", mask.sum(), "dtype:", mask.dtype)

# coordinates from dataset
import xarray as xr
ds0 = xr.open_dataset('/work/data/sst_20120601.nc', engine='h5netcdf')
lat = ds0['latitude'].values[329:390].copy()
lon = ds0['longitude'].values[550:611].copy()
ds0.close()
times = np.arange(np.datetime64('2012-06-01'), np.datetime64('2012-09-01'), dtype='datetime64[D]').astype('datetime64[ns]')
print("lat[0], lat[-1]:", lat[0], lat[-1], "| lon[0], lon[-1]:", lon[0], lon[-1])
print("lat[17], lat[18]:", lat[17], lat[18], "-> contains 60.09? ", lat[17] <= 60.09 <= lat[18])
print("times:", times[0], times[-1], len(times))

os.makedirs('/work/output', exist_ok=True)
dsm = xr.Dataset(
    {"mhw": (("time","lat","lon"), mask)},
    coords={"time": times, "lat": ("lat", lat), "lon": ("lon", lon)},
)
dsm["mhw"].attrs = {"long_name": "marine heatwave (per-cell) mask", "flag_values": np.array([0,1], dtype=np.uint8),
                    "flag_meanings": "not_in_mhw in_mhw", "units": "1"}
dsm.attrs = {
    "title": "Marine heatwave mask, Baltic Sea region 60.09-61.29N 20.01-21.21E, 2012-06-01..2012-08-31",
    "source": "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, DMI)",
    "method": "Hobday-style fixed 90th-percentile baseline threshold (1992-2002, +/-5-day day-of-year pools, hazen/quantile-type-5, 31-day circular moving-mean smoothing, Feb 29 filled from neighbours); per-cell MHW = >=5 consecutive hot days, gaps of 1-2 days joined",
    "note": "no per-cell MHWs detected in the target period; mask is all zeros",
}
enc = {"time": {"units": "seconds since 1981-01-01", "calendar": "proleptic_gregorian", "dtype": "float64"}}
dsm.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print("written /work/output/mhw_mask.nc")

# verify by reopening
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "sum:", int(chk['mhw'].values.sum()))
print("time values:", chk['time'].values[0], chk['time'].values[-1])
chk.close()
