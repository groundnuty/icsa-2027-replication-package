
import subprocess
r=subprocess.run(['python','/tmp/w/out.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout, r.stderr[-1000:])
import os; print(os.listdir('/work/output'))
import json; print(open('/work/output/report.json').read()[:600])
import xarray as xr; x=xr.open_dataset('/work/output/mhw_mask.nc'); print(x)
