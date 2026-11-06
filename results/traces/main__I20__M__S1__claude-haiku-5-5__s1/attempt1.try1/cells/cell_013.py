import subprocess
code=r'''
import numpy as np, xarray as xr, json, os, pandas as pd
r=np.load("/tmp/res.npz"); z=np.load("/tmp/sub.npz")
mhw=r["mhw"].astype(np.uint8); td=pd.to_datetime(r["tdates"])
lat=z["lat"].astype(np.float32); lon=z["lon"].astype(np.float32)
out="/work/output"; os.makedirs(out,exist_ok=True)
da=xr.DataArray(mhw,dims=("time","lat","lon"),coords={"time":td.values,"lat":lat,"lon":lon},name="mhw")
da.to_dataset().to_netcdf(out+"/mhw_mask.nc")
active=mhw.any(axis=(1,2)); i=0; n=len(active); events=[]
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append({"onset":str(td[i].date()),"end":str(td[j].date())}); i=j+1
    else: i+=1
rep={"region":{"lat_min":57.33,"lat_max":58.53,"lon_min":9.03,"lon_max":10.23},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2012-06-01","end":"2012-08-31"},
 "events":events,"complete":True,
 "caveats":"Sea cells = 3314 of 3600 region cells (finite SST on all target days). No cell had a run of >=5 consecutive hot days in Jun-Aug 2012 (longest hot run 3 days), so no per-cell or regional MHWs were found. Baseline windows extended to 1991-12-27..2003-01-05 as specified. Land and excluded cells set to 0."}
json.dump(rep,open(out+"/report.json","w"),indent=2)
print(events, mhw.shape, int(mhw.sum()))
'''
open("/tmp/write.py","w").write(code)
r=subprocess.run("cd /tmp && python write.py && ls -la /work/output && head -c 600 /work/output/report.json",shell=True,capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])