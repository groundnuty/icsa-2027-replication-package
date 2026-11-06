
import os, subprocess, shutil
print(os.getcwd(), os.path.exists('output'))
chk = r'''
import numpy as np, pandas as pd, json, xarray as xr
Z=np.load('/tmp/w/sub.npz', allow_pickle=True)
d=pd.to_datetime(Z['dates']); m=(d>='2021-06-01')&(d<='2021-08-31')
s=Z['sst'][m].astype(float)
print('summer SST mean', np.nanmean(s), 'min', np.nanmin(s), 'max', np.nanmax(s))
x=xr.open_dataset('/tmp/w/output/mhw_mask.nc')
print(x)
print(json.load(open('/tmp/w/output/report.json')))
'''
open('/tmp/w/chk.py','w').write(chk)
r=subprocess.run(['python','/tmp/w/chk.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-1500:])
