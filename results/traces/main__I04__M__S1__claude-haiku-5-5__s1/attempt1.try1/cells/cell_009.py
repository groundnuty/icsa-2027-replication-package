script = r'''
import numpy as np, pandas as pd, json, os
z=np.load("/tmp/sst_sub.npz"); A=z["A"]; dts=pd.to_datetime(z["dates"])
ref=pd.date_range("2000-01-01","2000-12-31")
doy_of_md={(d.month,d.day):i+1 for i,d in enumerate(ref)}
doy_all=np.array([doy_of_md[(d.month,d.day)] for d in dts])
ext_start,ext_end=pd.Timestamp("1991-12-27"),pd.Timestamp("2003-01-05")
bstart,bend=pd.Timestamp("1992-01-01"),pd.Timestamp("2002-12-31")
idx_of={d:i for i,d in enumerate(dts)}
ny,nx=A.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
base_dates=pd.date_range(bstart,bend)
for d in range(1,367):
    if d==60: continue
    bs=[b for b in base_dates if doy_of_md[(b.month,b.day)]==d]
    xs=set()
    for b in bs:
        for k in range(-5,6):
            x=b+pd.Timedelta(days=k)
            if ext_start<=x<=ext_end: xs.add(x)
    ii=[idx_of[x] for x in sorted(xs)]
    P=A[ii]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P,0.9,axis=0,method="hazen")
        clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
'''
open("/tmp/base.py","w").write(script)
exec_chk = r'''
exec(open("/tmp/base.py").read())
tgt=(dts>=pd.Timestamp("2020-06-01"))&(dts<=pd.Timestamp("2020-08-31"))
sea=np.isfinite(A[tgt]).all(axis=0)
print("sea cells",sea.sum(), "of",sea.size)
print("raw thr NaN days in sea cells:", np.isnan(thr[1:367][:,sea]).sum(), "clim:",np.isnan(clim[1:367][:,sea]).sum())
fin=np.isfinite(A).sum(axis=0)
print("finite baseline counts sea min/max", fin[sea].min(), fin[sea].max())
print("sea cells with any NaN in full series:", (~np.isfinite(A).all(axis=0))[sea].sum())
print("cells NaN-everywhere:", (fin==0).sum())
print("cells with NaN in full series overall:", (~np.isfinite(A).all(axis=0)).sum())
'''
open("/tmp/chk.py","w").write(exec_chk)
import subprocess
r=subprocess.run(["python","/tmp/chk.py"],capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])