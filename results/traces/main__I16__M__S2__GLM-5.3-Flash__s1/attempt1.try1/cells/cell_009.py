import numpy as np, json, os, warnings, xarray as xr
warnings.filterwarnings('ignore')
R=np.load('/tmp/results2.npz')
mem=R['mem']; events=R['events']; sea_cols=R['sea_cols']
T=np.load('/tmp/T.npy'); nt=T.shape[0]
ilat0,ilat1,ilon0,ilon1=(int(v) for v in np.load('/tmp/idx.npy'))
path='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(path, engine='h5netcdf')
time_vals=ds['time'].values[int(np.load('/tmp/t_idx.npy')[0]) : int(np.load('/tmp/t_idx.npy')[-1])+1]
lat_vals=ds['latitude'].values[ilat0:ilat1+1]
lon_vals=ds['longitude'].values[ilon0:ilon1+1]
nt_,nsea=mem.shape
assert time_vals.size==nt_==92 and lat_vals.size==60 and lon_vals.size==60
# scatter sea-column results into full 60x60 grid
grid=np.zeros((nt_,60,60),dtype=np.uint8)
rows,cols=np.divmod(sea_cols,60)
grid[:, rows, cols]=mem.astype(np.uint8)
os.makedirs('output',exist_ok=True)
dsout=xr.Dataset(
    {'mhw': (('time','lat','lon'), grid)},
    coords={'time':('time',time_vals), 'lat':('lat',lat_vals), 'lon':('lon',lon_vals)},
)
dsout['mhw'].attrs={'long_name':'marine heatwave (per-cell) mask', 'flag_values':np.array([0,1],dtype=np.uint8),
                    'flag_meanings':'not_in_mhw in_mhw', 'units':'1'}
dsout['time'].encoding={'units':'seconds since 1981-01-01','calendar':'proleptic_gregorian','dtype':'int32'}
dsout.attrs={'title':'Per-cell marine heatwave mask, Baltic Sea region, 2008-06-01..2008-08-31',
             'dataset':'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
             'baseline':'1992-01-01..2002-12-31 pools (windows 1991-12-27..2003-01-05), 90th pct hazen, 31-day circular smooth'}
dsout.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')

ev=[[str(np.datetime64('2008-06-01')+np.timedelta64(int(s),'D')), str(np.datetime64('2008-06-01')+np.timedelta64(int(e),'D'))] for s,e in events.tolist()]
report={
 "region": {"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},
 "baseline_analysed": {"start":"1991-12-27","end":"2003-01-05"},
 "target_analysed": {"start":"2008-06-01","end":"2008-08-31"},
 "events": [{"onset":a,"end":b} for a,b in ev],
 "complete": True,
 "caveats": ("SST used as stored (float32, kelvin), promoted to float64 for statistics. "
   "Sea cells: 3304 of 3600 region cells (finite on all analysed days). Threshold/climatology pools from "
   "baseline dates 1992-01-01..2002-12-31 with +/-5-day windows (1991-12-27..2003-01-05); day 60 filled from "
   "days 59/61; both smoothed with circular 31-day mean. Hot day: SST >= threshold (hazen 90th percentile). "
   "Per-cell MHW: >=5 hot days, gaps of 1-2 days joined. Regional events from daily max over sea cells: "
   "1 event, 9 active days of 92.")
}
with open('output/report.json','w') as f: json.dump(report,f,indent=1)

# ---- read back and verify ----
v=xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("vars:", list(v.variables), "| dims:", dict(v.sizes))
m=v['mhw']; print("mhw dtype:", m.dtype, "| vals:", np.unique(m.values))
mv=m.values
print("mask equals mem on sea cols:", bool((mv[:,rows,cols]==mem.astype(np.uint8)).all()), "| land all zero:", bool(mv[:, np.setdiff1d(np.arange(3600), sea_cols)].max()==0))
print("time first/last:", str(v['time'].values[0])[:10], str(v['time'].values[-1])[:10])
print("lat range:", float(v['lat'][0]), float(v['lat'][-1]), "| lon range:", float(v['lon'][0]), float(v['lon'][-1]))
r=json.load(open('output/report.json'))
print("report fields:", list(r.keys()))
print(json.dumps({k:r[k] for k in ('baseline_analysed','target_analysed','events','complete')}, indent=1))
print("active days from file:", int((mv.reshape(nt_,-1).max(axis=1)>0).sum()))
print("files:", os.path.exists('output/mhw_mask.nc'), os.path.exists('output/report.json'),
      "| sizes:", os.path.getsize('output/mhw_mask.nc'), os.path.getsize('output/report.json'))
