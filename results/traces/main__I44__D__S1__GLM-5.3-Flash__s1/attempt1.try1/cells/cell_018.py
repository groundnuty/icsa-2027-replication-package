import numpy as np, datetime as dt, json, os
import xarray as xr
import h5py

fin=np.load('/work/final.npz')
sea=fin['sea']; mhw=fin['mhw']
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh) if False else None
import pickle
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
d0=dates[0]
t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
tdates=dates[ti0:ti1+1]
print('target days:', len(tdates), tdates[0], tdates[-1])

# dataset coordinate values from a source file
with h5py.File('/work/nc/sst_20040615.nc','r') as f:
    lat32=f['latitude'][:]; lon32=f['longitude'][:]
latv=lat32[491:551]; lonv=lon32[616:676]
tv=(np.array([(d-dt.date(1981,1,1)).days for d in tdates], dtype=np.int64)*86400).astype(np.int32)
print('time first/last (s):', tv[0], tv[-1], '->', dt.date(1981,1,1)+dt.timedelta(seconds=int(tv[0])), dt.date(1981,1,1)+dt.timedelta(seconds=int(tv[-1])))

mask=mhw.astype(np.uint8)
# land cells must be 0
assert mask[:, ~sea].sum()==0
print('mask shape/dtype:', mask.shape, mask.dtype, 'ones:', int(mask.sum()))

ds=xr.Dataset(
    {'mhw': (('time','lat','lon'), mask)},
    coords={'time': ('time', tv), 'lat': ('lat', latv), 'lon': ('lon', lonv)},
)
ds['lat'].attrs={'long_name':'latitude','units':'degrees_north','standard_name':'latitude','axis':'Y'}
ds['lon'].attrs={'long_name':'longitude','units':'degrees_east','standard_name':'longitude','axis':'X'}
ds['mhw'].attrs={'long_name':'marine heatwave (per-cell) mask','units':'1',
                 'flag_values':np.array([0,1],dtype=np.uint8),
                 'flag_meanings':'not_in_mhw in_mhw',
                 'comment':'1 where the cell is inside a per-cell MHW on that day (runs >=5 hot days, gaps <=2 days joined); land cells are 0. Region: 63.31-64.51N, 21.31-22.51E; target 2004-06-01..2004-08-31; thresholds from 1992-2002 baseline, hazen p90 of +-5-day day-of-year pools, 31-day circular smoothing.'}
ds['time'].attrs={'long_name':'Time','standard_name':'time','axis':'T'}
os.makedirs('/work/output', exist_ok=True)
enc={'time':{'dtype':'int32','units':'seconds since 1981-01-01','calendar':'proleptic_gregorian'},
     'lat':{'dtype':'float32'},'lon':{'dtype':'float32'},
     'mhw':{'dtype':'uint8','_FillValue':None,'zlib':True,'complevel':4}}
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print('wrote mhw_mask.nc, size:', os.path.getsize('/work/output/mhw_mask.nc'))

report={
 "region": {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51},
 "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
 "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
 "events": [{"onset": "2004-08-07", "end": "2004-08-12"}],
 "complete": True,
 "caveats": "Dataset cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (daily analysed_sst, kelvin), one file per day; region grid: 60x60 cells at 0.02 deg (lat 63.32-64.50, lon 21.32-22.50), of which 3299 sea cells (SST finite on all 92 target days) and 301 land cells. Thresholds and climatology from baseline 1992-01-01..2002-12-31 via +-5-calendar-day day-of-year pools (window edges extend to 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; 29 Feb values belong to neighbouring doy pools; doy 60 filled as mean of doy 59 and 61), Hazen (type 5) 90th percentile, then unweighted centred 31-day circular moving mean. Per-cell MHWs: hot = SST >= threshold, runs >= 5 days, gaps <= 2 days joined; detection restricted to the target period. One regional event (2004-08-07..2004-08-12); 201 of 3299 sea cells had >= 1 MHW day."
}
with open('/work/output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print('wrote report.json, size:', os.path.getsize('/work/output/report.json'))
