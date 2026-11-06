import subprocess, os
s=open('/tmp/x/run.py').read().replace("os.makedirs('output',exist_ok=True)","os.makedirs('/work/output',exist_ok=True)").replace("'output/mhw_mask.nc'","'/work/output/mhw_mask.nc'").replace("open('output/report.json','w')","open('/work/output/report.json','w')")
s+="\nprint('thr sample', [round(float(thr_s[d,sea.nonzero()[0][0]]),2) for d in (1,60,152,200,244,366)], 'clim', [round(float(clim_s[d,sea.nonzero()[0][0]]),2) for d in (152,200)])\n"
open('/tmp/x/run.py','w').write(s)
r=subprocess.run(['python','/tmp/x/run.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout[-2000:], r.stderr[-500:])
import xarray as xr, json
ds=xr.open_dataset('/work/output/mhw_mask.nc'); print(ds); print(json.load(open('/work/output/report.json')))
