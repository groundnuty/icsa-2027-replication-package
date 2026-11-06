import numpy as np, datetime as dt, json, os, pickle
from netCDF4 import Dataset

fin=np.load('/work/final.npz')
sea=fin['sea']; mhw=fin['mhw']
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
d0=dates[0]
t_start=dt.date(2004,6,1); t_end=dt.date(2004,8,31)
ti0=(t_start-d0).days; ti1=(t_end-d0).days
tdates=dates[ti0:ti1+1]

import h5py
with h5py.File('/work/nc/sst_20040615.nc','r') as f:
    lat32=f['latitude'][:]; lon32=f['longitude'][:]
latv=lat32[491:551]; lonv=lon32[616:676]
tv=(np.array([(d-dt.date(1981,1,1)).days for d in tdates],dtype=np.int64)*86400).astype(np.int32)
mask=mhw.astype(np.uint8)
assert mask[:, ~sea].sum()==0 and mask.shape==(92,60,60)

p='/work/output/mhw_mask.nc'
if os.path.exists(p): os.remove(p)
os.makedirs('/work/output', exist_ok=True)
nc=Dataset(p,'w',format='NETCDF4')
nc.createDimension('time',92); nc.createDimension('lat',60); nc.createDimension('lon',60)
vt=nc.createVariable('time','i4',('time',))
vt[:]=tv
vt.units='seconds since 1981-01-01'; vt.calendar='proleptic_gregorian'
vt.long_name='Time'; vt.standard_name='time'; vt.axis='T'
vla=nc.createVariable('lat','f4',('lat',)); vla[:]=latv
vla.units='degrees_north'; vla.standard_name='latitude'; vla.long_name='latitude'; vla.axis='Y'
vlo=nc.createVariable('lon','f4',('lon',)); vlo[:]=lonv
vlo.units='degrees_east'; vlo.standard_name='longitude'; vlo.long_name='longitude'; vlo.axis='X'
vm=nc.createVariable('mhw','u1',('time','lat','lon'), zlib=True, complevel=4, fill_value=False)
vm[:]=mask
vm.long_name='marine heatwave (per-cell) mask'; vm.units='1'
vm.flag_values=np.array([0,1],dtype=np.uint8); vm.flag_meanings='not_in_mhw in_mhw'
vm.comment=('1 where the cell is inside a per-cell MHW on that day (hot = SST >= 90th-percentile threshold, '
            'runs >=5 days, gaps of 1-2 days joined); land cells are 0. Region 63.31-64.51N, 21.31-22.51E; '
            'target 2004-06-01..2004-08-31; baseline 1992-2002 (hazen p90 of +-5-day doy pools, 31-day circular smoothing).')
nc.Conventions='CF-1.8'
nc.title='Marine heatwave mask, Baltic Sea region (63.31-64.51N, 21.31-22.51E), June-August 2004'
nc.source='cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (Copernicus Marine SST_BAL_SST_L4_REP_OBSERVATIONS_010_016)'
nc.close()
print('wrote', p, os.path.getsize(p), 'bytes')

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
print('wrote /work/output/report.json', os.path.getsize('/work/output/report.json'), 'bytes')
