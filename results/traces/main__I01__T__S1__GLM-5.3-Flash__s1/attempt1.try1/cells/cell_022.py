import numpy as np, json, os, datetime as dt
from netCDF4 import Dataset

z1 = np.load('/work/cache_stage1.npz')
z3 = np.load('/work/cache_stage3.npz')
mhw = z3['mhw_span']                       # (92, 3600) bool
lat_r = z1['lat_r']; lon_r = z1['lon_r']   # dataset float32 values
ttimes = z1['ttimes'].astype('datetime64[D]')
nlat, nlon = len(lat_r), len(lon_r)
mask = mhw.reshape(len(ttimes), nlat, nlon).astype(np.uint8)
print('mask shape', mask.shape, 'cell-days in MHW:', int(mask.sum()))

os.makedirs('output', exist_ok=True)

# ---- mhw_mask.nc ----
with Dataset('output/mhw_mask.nc', 'w', format='NETCDF4') as nc:
    nc.createDimension('time', len(ttimes))
    nc.createDimension('lat', nlat)
    nc.createDimension('lon', nlon)
    tv = nc.createVariable('time', 'f8', ('time',))
    tv.units = 'days since 1950-01-01 00:00:00'
    tv.calendar = 'proleptic_gregorian'
    tv.standard_name = 'time'
    tv.axis = 'T'
    tv[:] = (ttimes - np.datetime64('1950-01-01', 'D')).astype('int64')
    yv = nc.createVariable('lat', 'f4', ('lat',))
    yv.units = 'degrees_north'; yv.standard_name = 'latitude'; yv.axis = 'Y'
    yv[:] = lat_r
    xv = nc.createVariable('lon', 'f4', ('lon',))
    xv.units = 'degrees_east'; xv.standard_name = 'longitude'; xv.axis = 'X'
    xv[:] = lon_r
    mv = nc.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), zlib=True, complevel=4)
    mv.long_name = 'per-cell marine heatwave mask (1 = cell inside a per-cell MHW)'
    mv.coordinates = 'time lat lon'
    mv[:] = mask
    nc.title = 'Marine heatwave mask, Baltic Sea region, 2008-06-01 to 2008-08-31'
    nc.source = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, version 202506)'
    nc.method = 'Baseline 1992-2002; per cell and day-of-year +/-5 calendar-day pools; 90th percentile (Hazen); 31-day circular moving mean; hot >= threshold; runs >= 5 days; gaps of 1-2 days joined'
print('wrote output/mhw_mask.nc')

# ---- report.json ----
report = {
    "region": {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
    "events": [{"onset": "2008-06-01", "end": "2008-06-21"}],
    "complete": True,
    "caveats": ("Thresholds and climatology use the 1992-2002 baseline with +/-5 calendar-day "
                "pools (including up to 5 days beyond the baseline at each end) and a circular "
                "31-day moving mean; per-cell hot runs were searched within the target period "
                "only, so runs truncated at the period edges count from their first in-period "
                "day. Dataset version 202506.")
}
with open('output/report.json', 'w') as fp:
    json.dump(report, fp, indent=2)
print('wrote output/report.json')
print(json.dumps(report, indent=2))
