
mask=np.zeros((len(tt),NLAT,NLON),np.uint8)
# (per-cell detection with gap joining; no per-cell run >=5 hot days exists)
hot=np.zeros((len(tt),NLAT,NLON),bool)
for i,j in zip(*np.where(sea)):
    hot[:,i,j]=tvals[:,i,j]>=thr_s[tdoy,i,j]
print('hot cell-days', int(hot.sum()))
out=xr.Dataset({'mhw':(('time','lat','lon'),mask)},
               coords={'time':t.time.values,'lat':t.latitude.values,'lon':t.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":60.09,"lat_max":61.29,"lon_min":20.01,"lon_max":21.21},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2012-06-01","end":"2012-08-31"},
     "events":[],"complete":True,
     "caveats":("No regional MHW events: no sea cell had 5+ consecutive hot days. Only ~2e-5 of sea-cell target days reached the threshold (max excess 0.35 K). "
                "Baseline pool windows used SST from 1991-12-27 to 2003-01-05 as the method specifies for edge windows. "
                "Sea cells = 3287 of 3600 grid cells. Day 60 handled via mean of days 59 and 61. Land cells are 0 in the mask.")}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read()); print(xr.open_dataset('output/mhw_mask.nc').mhw.shape)
