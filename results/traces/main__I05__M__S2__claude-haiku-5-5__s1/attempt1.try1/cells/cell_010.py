
out = r'''
exec(open('/tmp/w/run.py').read())
import xarray as xr, os
os.makedirs('/tmp/out',exist_ok=True)
os.makedirs('output',exist_ok=True)
mask=mhw.reshape(len(tt),len(lat),len(lon)).astype(np.uint8)
da=xr.DataArray(mask,dims=('time','lat','lon'),coords={'time':tt.values,'lat':lat,'lon':lon},name='mhw')
da.to_dataset().to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":[{"onset":a,"end":b} for a,b in events],
 "complete":True,
 "caveats":("Event onset 2021-06-01 equals the first target day, so it is left-truncated by the target window (per spec, no data outside it used); "
   "the event may have begun earlier. Threshold/climatology use 1992-2002 with the 1991-12-27..2003-01-05 margins. "
   "Only the 3309 cells finite on all target days are sea cells; land/partly-missing cells are 0 in the mask. "
   "Summer 2021 is ~3 K above the baseline mean, so most sea cells are hot on most days (about 58% of cell-days), which is a genuine anomaly but makes the event very large.")}
json.dump(rep,open('output/report.json','w'),indent=2)
print(rep['events'], mask.shape, mask.sum())
'''
open('/tmp/w/out.py','w').write(out)
import subprocess
r=subprocess.run(['python','/tmp/w/out.py'],capture_output=True,text=True,cwd='/tmp/w')
print(r.stdout, r.stderr[-2000:])
