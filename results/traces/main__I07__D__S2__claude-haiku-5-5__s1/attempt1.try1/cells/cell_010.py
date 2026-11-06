
code3 = r'''
import numpy as np, pandas as pd, json, os, xarray
exec(open('/work/s1.py').read().split("# sea cells")[0].replace("print(","(lambda *a,**k: None)("))
z=np.load('/work/thr.npz'); thr366=z['thr']; clim366=z['clim']; sea=z['sea']; ti=z['ti']
tt = dates[ti]
dd = doys[ti]
Ts = A[ti]  # target SST
H = np.zeros(Ts.shape, bool)
H = Ts >= thr366[dd-1]   # shape (nt,NY,NX) via fancy index
H &= sea[None]
nt = len(ti)
mhw = np.zeros((nt,NY,NX), bool)
def runs(b):
    out=[]; i=0; n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append([i,j]); i=j+1
        else: i+=1
    return out
ncell=0
for y in range(NY):
    for x in range(NX):
        if not sea[y,x]: continue
        ev=[r for r in runs(H[:,y,x]) if r[1]-r[0]+1>=5]
        if not ev: continue
        merged=[ev[0]]
        for r in ev[1:]:
            if r[0]-merged[-1][1]-1 <= 2: merged[-1]=[merged[-1][0], r[1]]
            else: merged.append(r)
        ncell+=len(merged)
        for a,b in merged: mhw[a:b+1,y,x]=True
print('per-cell MHW count', ncell, 'cell-days', mhw.sum())
active = mhw.any(axis=(1,2))
events=[]
for a,b in runs(active):
    events.append({'onset':str(pd.Timestamp(tt[a]).date()),'end':str(pd.Timestamp(tt[b]).date())})
print(events)
print('active days', active.sum(), 'target days', nt, tt[0], tt[-1])
os.makedirs('/work/output',exist_ok=True)
os.makedirs('/work/output',exist_ok=True)
lat=ds.latitude.values[ilat]; lon=ds.longitude.values[ilon]
out = xarray.Dataset({'mhw': (('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time': ds.time.values[tidx][ti], 'lat': lat, 'lon': lon})
out['mhw'].attrs={'long_name':'marine heatwave flag'}
out.to_netcdf('/work/output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8'}})
rep = {'region': {'lat_min':54.45,'lat_max':55.65,'lon_min':16.05,'lon_max':17.25},
 'baseline_analysed': {'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed': {'start':str(pd.Timestamp(tt[0]).date()),'end':str(pd.Timestamp(tt[-1]).date())},
 'events': events, 'complete': True,
 'caveats': 'Land cells (308 of 3600 grid cells, always NaN) and cells with NaN in target period are excluded as non-sea; the pool uses the leap-year day-of-year mapping per spec; the 5 extra days at each baseline end were included as specified. Region grid cells are lat 54.46-55.64, lon 16.06-17.24 (the grid points inside the bounds).'}
json.dump(rep, open('/work/output/report.json','w'), indent=2)
print('written')
'''
open('/work/s3.py','w').write(code3)
r=subprocess.run(['python','/work/s3.py'],capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-1500:])
