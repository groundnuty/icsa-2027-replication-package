
os.makedirs('output',exist_ok=True)
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':tgt_t.values,'lat':latr,'lon':lonr})
ds_out.to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':54.17,'lat_max':55.37,'lon_min':13.25,'lon_max':14.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2014-06-01','end':'2014-08-31'},
 'events':[{'onset':a,'end':b} for a,b in events],
 'complete':True,
 'caveats':('SST loaded from sst_s2.nc (1982-2023), the only file covering 1992-2002 and 2014; '
   'the s1z files cover only 1982-1984. Threshold pool uses the margin days 1991-12-27..31 and 2003-01-01..05. '
   'Feb 29 handled by real-date windows. Non-sea cells (not finite on all target days) are excluded and masked 0. '
   'Events are merged runs of regional active days.')}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read()[:600])
print(xr.open_dataset('output/mhw_mask.nc').mhw.shape)
