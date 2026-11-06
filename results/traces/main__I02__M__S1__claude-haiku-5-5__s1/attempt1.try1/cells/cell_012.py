
s3 = open('/tmp/run.py').read().split("os.makedirs")[0] + r'''
os.makedirs('output',exist_ok=True)
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':(('time',),np.array([np.datetime64(t.isoformat()) for t in tdays],dtype='datetime64[ns]')),
            'lat':(('lat',),LAT),'lon':(('lon',),LON)})
ds_out.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2004-06-01","end":"2004-08-31"},
     "events":events,"complete":True,
     "caveats":"Grid cells of the 0.02 deg product in the box: 60x60 (lat 54.18-55.36, lon 13.26-14.44 as stored). 3303 of 3600 cells are sea cells (finite all target days). Baseline threshold/climatology from 1992-2002 pools with +/-5 day windows (including 1991-12-27..1991-12-31 and 2003-01-01..05). No per-cell MHW (>=5 consecutive hot days) occurred in the target period, so no regional events were found. Mask has 92 target days; non-sea cells are 0."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(json.dumps(rep)[:500])
'''
open('/tmp/final.py','w').write(s3)
import subprocess
r=subprocess.run(['python','/tmp/final.py'],capture_output=True,text=True,cwd='/tmp'); print(r.stdout, r.stderr[-2000:])
r=subprocess.run(['python','-c',"import xarray as xr;x=xr.open_dataset('/tmp/output/mhw_mask.nc');print(x)"],capture_output=True,text=True); print(r.stdout[:800], r.stderr[-500:])