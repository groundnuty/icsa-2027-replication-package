
T=len(ttime)
doys=np.array([doy(t) for t in ttime])-1  # 0-based index into 366
th=thrS[doys]  # T,ny,nx
hot=(tgt>=th)&np.isfinite(th)&np.isfinite(tgt)
hot &= sea[None]
mhw=np.zeros((T,ny,nx),dtype=bool)
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        runs=[];t=0
        while t<T:
            if h[t]:
                s=t
                while t<T and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        # join gaps of 1-2 days
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2:
                merged[-1][1]=r[1]
            else: merged.append(r[:])
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[];t=0
while t<T:
    if active[t]:
        s=t
        while t<T and active[t]: t+=1
        events.append({"onset":str(ttime[s].date()),"end":str(ttime[t-1].date())})
    else: t+=1
print(events, mhw.sum(), active.sum())
os.makedirs('output',exist_ok=True)
lat=sub.latitude.values; lon=sub.longitude.values
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':ttime.values,'lat':lat,'lon':lon})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":events,"complete":True,
 "caveats":"Grid 60x60 cells (dataset native 0.02 deg); 3296 sea cells with finite SST all target days; land cells 0. Baseline pool uses 121 values per day of year. Threshold/climatology computed in float64 from float32 stored values. Climatology computed but not output."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read()[:600])
