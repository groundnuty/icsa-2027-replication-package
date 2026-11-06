
os.makedirs('/data/../'+'/tmp/out',exist_ok=True) if False else None
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
               coords={'time':ttime.values,'lat':latv.astype(np.float32),'lon':lonv.astype(np.float32)})
out.mhw.attrs={'long_name':'marine heatwave per-cell flag'}
out.to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
rep={"region":{"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2019-06-01","end":"2019-08-31"},
     "events":ev,"complete":True,
     "caveats":"Day-of-year mapping uses leap-year table (Mar 1 = 61 in all years) as specified. Land cells (300 of 3600) are NaN and set to 0. Baseline pools use calendar windows that extend into 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. Only 17 active days in one event; no other events."}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf'); print(chk.mhw.dims, chk.mhw.shape, chk.mhw.dtype, chk.mhw.values.sum())
print(open('output/report.json').read()[:400])
