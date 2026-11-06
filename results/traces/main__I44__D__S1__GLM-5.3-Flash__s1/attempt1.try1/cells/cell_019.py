import numpy as np, datetime as dt, json, os, pickle
import xarray as xr
import h5py

fin=np.load('/work/final.npz')
sea=fin['sea']; mhw=fin['mhw']
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
d0=dates[0]
t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
tdates=dates[ti0:ti1+1]

with h5py.File('/work/nc/sst_20040615.nc','r') as f:
    lat32=f['latitude'][:]; lon32=f['longitude'][:]
latv=lat32[491:551]; lonv=lon32[616:676]
tv=(np.array([(d-dt.date(1981,1,1)).days for d in tdates], dtype=np.int64)*86400).astype(np.int32)

mask=mhw.astype(np.uint8)
assert mask[:, ~sea].sum()==0

ds=xr.Dataset(
    {'mhw': (('time','lat','lon'), mask)},
    coords={'time': ('time', tv), 'lat': ('lat', latv), 'lon': ('lon', lonv)},
)
ds['lat'].attrs={'long_name':'latitude','units':'degrees_north','standard_name':'latitude','axis':'Y'}
ds['lon'].attrs={'long_name':'longitude','units':'degrees_east','standard_name':'longitude','axis':'X'}
ds['time'].attrs={'long_name':'Time','standard_name':'time','axis':'T'}
ds['mhw'].attrs={'long_name':'marine heatwave (per-cell) mask','units':'1',
                 'flag_values':np.array([0,1],dtype=np.uint8),
                 'flag_meanings':'not_in_mhw in_mhw',
                 'comment':'1 where the cell is inside a per-cell MHW on that day (hot = SST >= 90th-pct threshold, runs >=5 days, gaps <=2 days joined); land cells are 0. Region 63.31-64.51N, 21.31-22.51E; target 2004-06-01..2004-08-31; baseline 1992-2002.'}
os.makedirs('/work/output', exist_ok=True)
if os.path.exists('/work/output/mhw_mask.nc'): os.remove('/work/output/mhw_mask.nc')
enc={'time':{'dtype':'int32','units':'seconds since 1981-01-01','calendar':'proleptic_gregorian'},
     'lat':{'dtype':'float32'},'lon':{'dtype':'float32'},
     'mhw':{'dtype':'uint8','_FillValue':None,'zlib':True,'complevel':4}}
ds.to_netcdf('/work/output/mhw_mask.nc', engine='netcdf4', encoding=enc, format='NETCDF4')
print('wrote mhw_mask.nc, size:', os.path.getsize('/work/output/mhw_mask.nc'))

report={
 "region": {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51},
 "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
 "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
 "events": [{"onset": "2004-08-07", "end": "2004-08-12"}],
 "complete": True,
 "caveats": "Dataset cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (analysed_sst, kelvin, daily, one NetCDF per day). Region grid: 60x60 cells at 0.02 deg (lat 63.32-64.50, lon 21.32-22.50); 3299 sea cells (SST finite on all 92 target days) and 301 land cells (mask 0). Thresholds and climatology from baseline 1992-01-01..2002-12-31 via +-5-calendar-day day-of-year pools (edge windows reach 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; 29 Feb values included in the pools of neighbouring doys; doy 60 set to the mean of doy 59 and 61), 90th percentile with Hazen (Hyndman-Fan type 5) definition, then unweighted centred 31-day moving mean wrapping around the 366-day year. Hot day: SST >= smoothed threshold. Per-cell MHW: runs >= 5 hot days, gaps of 1-2 non-hot days joined (gap days included), detection restricted to 2004-06-01..2004-08-31. Regional events: runs of days with at least one sea cell inside a per-cell MHW. Result: one regional event, 2004-08-07..2004-08-12 (6 days); 201 of 3299 sea cells had at least one MHW day; 1073 MHW cell-days in total."
}
with open('/work/output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print('wrote report.json, size:', os.path.getsize('/work/output/report.json'))
