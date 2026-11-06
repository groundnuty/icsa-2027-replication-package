import subprocess
code2 = open('/tmp/w/run.py').read().replace("os.makedirs('/mnt/output',exist_ok=True)\n","")
code2 += r'''
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':('time',np.array([np.datetime64(d) for d in tdates],dtype='datetime64[ns]')),
            'lat':('lat',lat),'lon':('lon',lon)})
ds.to_netcdf('output/mhw_mask.nc',encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={"region":{"lat_min":55.67,"lat_max":56.87,"lon_min":16.45,"lon_max":17.65},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2005-06-01","end":"2005-08-31"},
     "events":events,"complete":True,
     "caveats":"Land cells (NaN in target) are not sea cells and are 0. Baseline pools use calendar windows of +/-5 days incl. the 1991-12-27..2003-01-05 extension. Only the region's 60x60 grid cells (lat 55.68-56.86, lon 16.46-17.64) exist within the bounds."}
json.dump(rep,open('output/report.json','w'),indent=2)
print('written', os.path.abspath('output'))
'''
open('/tmp/w/run2.py','w').write(code2)
r=subprocess.run(['python','/tmp/w/run2.py'],capture_output=True,text=True,cwd='/tmp/w'); print(r.stdout, r.stderr[-800:])
print(subprocess.run("cat /tmp/w/output/report.json; python -c \"import xarray as xr;d=xr.open_dataset('/tmp/w/output/mhw_mask.nc');print(d)\"",shell=True,capture_output=True,text=True).stdout)