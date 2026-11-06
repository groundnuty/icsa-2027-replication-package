run = r'''
exec(open("/tmp/base.py").read())
import xarray as xr
def smooth(arr):
    v=arr[1:367]
    out=np.empty_like(v)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(v[ids],axis=0)
    return out
T=smooth(thr); C=smooth(clim)
tgt=(dts>=pd.Timestamp("2020-06-01"))&(dts<=pd.Timestamp("2020-08-31"))
S=A[tgt]; td=dts[tgt]; dd=doy_all[tgt]
sea=np.isfinite(S).all(axis=0)
ntd,ny,nx=S.shape
thr_t=T[dd-1]   # per target day, cell
hot=(S>=thr_t)&sea[None]
mhw=np.zeros((ntd,ny,nx),dtype=np.uint8)
for j in range(ny):
    for i in range(nx):
        if not sea[j,i]: continue
        h=hot[:,j,i]
        # runs of hot
        segs=[]; t=0
        while t<ntd:
            if h[t]:
                s=t
                while t<ntd and h[t]: t+=1
                if t-s>=5: segs.append([s,t-1])
            else: t+=1
        # join segments separated by 1 or 2 non-hot days
        merged=[]
        for sg in segs:
            if merged and (sg[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=sg[1]
            else: merged.append(list(sg))
        for s,e in merged: mhw[s:e+1,j,i]=1
active=mhw.reshape(ntd,-1).any(axis=1)
events=[]; t=0
while t<ntd:
    if active[t]:
        s=t
        while t<ntd and active[t]: t+=1
        events.append({"onset":str(td[s].date()),"end":str(td[t-1].date())})
    else: t+=1
print("sea cells",sea.sum(),"active days",active.sum(),"events",events)
print("cells with any MHW", (mhw.sum(axis=0)>0).sum(), "mhw cell-days", mhw.sum())
# coords from a file
with xr.open_dataset(f"{D}/sst_20200615.nc",engine="h5netcdf") as x:
    lat=x.latitude.values[45:105]; lon=x.longitude.values[463:523]
out=xr.Dataset({"mhw":(("time","lat","lon"),mhw)},
    coords={"time":td.values,"lat":lat,"lon":lon})
os.makedirs("/tmp/output",exist_ok=True)
out.to_netcdf("/tmp/output/mhw_mask.nc")
rep={"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2020-06-01","end":"2020-08-31"},
     "events":events,"complete":True,
     "caveats":"Baseline windows used days 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 as specified. Land/non-sea cells (any NaN in target period) are 0. Per-cell gap-joining done in a single pass."}
json.dump(rep,open("/tmp/output/report.json","w"),indent=2)
print("written")
'''
open("/tmp/run.py","w").write(run)
r=subprocess.run(["python","/tmp/run.py"],capture_output=True,text=True); print(r.stdout[-6000:], r.stderr[-1500:])