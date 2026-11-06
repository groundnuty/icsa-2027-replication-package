
import warnings; warnings.filterwarnings('ignore')
exec(open('/work/common.py').read())
nT=len(Tt)
thr_t = thr[Dt-1]
hot = (At>=thr_t) & sea[None]
mhw = np.zeros((nT,60,60),dtype=np.uint8)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h = hot[:,i,j]; runs=[]; k=0
        while k<nT:
            if h[k]:
                s=k
                while k<nT and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1) in (1,2): merged[-1][1]=r[1]
            else: merged.append(r[:])
        for s,e in merged: mhw[s:e+1,i,j]=1
active = mhw.reshape(nT,-1).any(axis=1)
events=[]; k=0
while k<nT:
    if active[k]:
        s=k
        while k<nT and active[k]: k+=1
        events.append({"onset":str(Tt[s].date()),"end":str(Tt[k-1].date())})
    else: k+=1
ds_out = xr.Dataset({'mhw':(('time','lat','lon'), mhw)},
    coords={'time':Tt.values.astype('datetime64[ns]'), 'lat':latr, 'lon':lonr})
ds_out['mhw'].attrs={}
ds_out.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8'}})
report={"region":{"lat_min":57.33,"lat_max":58.53,"lon_min":9.03,"lon_max":10.23},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":events,"complete":True,
 "caveats":"Region bounds as specified; the dataset grid inside it is lat 57.34-58.52 and lon 9.04-10.22 (60x60 cells). Only the 3314 cells finite on all target days are sea cells; other cells are 0 in the mask. Thresholds are finite for all sea cells. Smoothing uses plain mean over the 31-day window. 2021 target days are analysed with leap-year day-of-year mapping as specified."}
json.dump(report, open('output/report.json','w'), indent=2)
print(json.dumps(report,indent=1)[:1500])
print(xr.open_dataset('output/mhw_mask.nc').mhw.shape, mhw.sum())
