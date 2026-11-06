import os, json
os.makedirs('output',exist_ok=True)
times=np.array([np.datetime64(d.isoformat()) for d in tgt_dates],dtype='datetime64[ns]')
da=xr.DataArray(mhw.astype(np.uint8),dims=('time','lat','lon'),coords={'time':times,'lat':lat.astype(np.float32),'lon':lon.astype(np.float32)},name='mhw')
da.to_dataset().to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
rep={"region":{"lat_min":54.81,"lat_max":56.01,"lon_min":19.61,"lon_max":20.81},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2007-06-01","end":"2007-08-31"},
     "events":[{"onset":a.isoformat(),"end":b.isoformat()} for a,b in ev],
     "complete":True,
     "caveats":"Sea cells = 3289 of 3600 region cells (finite on all target days). Pools use the 1991-12-27 to 2003-01-05 window; 121 values per day of year. Per-cell MHWs are merged across gaps of up to 2 days. Land cells are 0 in the mask. Output coordinates are the dataset's float32 lat/lon values, and the time coordinate is the 92 target days."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
chk=xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf'); print(chk.mhw.dtype, chk.mhw.shape, int(chk.mhw.sum()))