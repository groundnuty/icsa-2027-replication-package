import numpy as np, json, os, datetime as dt, xarray as xr
os.makedirs('/work/output',exist_ok=True)
os.makedirs('output',exist_ok=True)
g=np.load('/work/grid.npz'); lat=g['lat'].astype(np.float32); lon=g['lon'].astype(np.float32)
m=np.load('/work/out/mhw.npy'); events=json.load(open('/work/out/events.json'))
times=np.array([np.datetime64(dt.date(2021,6,1)+dt.timedelta(i)) for i in range(92)],dtype='datetime64[ns]')
da=xr.DataArray(m,dims=('time','lat','lon'),coords={'time':times,'lat':lat,'lon':lon},name='mhw').astype(np.uint8)
da.to_dataset().to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":events,"complete":True,
 "caveats":"Region trimmed to the 60x60 grid cells with coordinates inside the bounds (lat 54.40-55.58, lon 18.26-19.44). 3309 of 3600 cells are sea cells (finite all target days). Thresholds use 121-value pools per day of year (11 baseline years x 11-day window), hazen quantile, smoothing as specified. Gap joining applied to per-cell MHWs with 1-2 day gaps. Result: one regional event 2021-06-01 to 2021-08-05 (the event is already active on the first target day, so its true onset may precede the target period). The hot fraction is very high (about 90% of sea cells in MHW for much of June-July), so results are sensitive to the baseline threshold."}
json.dump(rep,open('output/report.json','w'),indent=1)
print(xr.open_dataset('output/mhw_mask.nc'))
print(open('output/report.json').read()[:600])