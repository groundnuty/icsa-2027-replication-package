import subprocess
chk=r'''
import xarray as xr, json, numpy as np
m=xr.open_dataset('/work/output/mhw_mask.nc'); print(m); print(m.mhw.dtype, int(m.mhw.sum()))
print(json.load(open('/work/output/report.json')))
'''
open('/tmp/chk.py','w').write(chk)
print(subprocess.run("python /tmp/chk.py", shell=True, capture_output=True, text=True).stdout[-3000:])